import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import sqlite3
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
try:
    from weasyprint import HTML
except Exception as e:
    print(f"weasyprint not available: {e}")
    HTML = None

# --- App Initialization and Configuration ---
# Load environment variables from .env file (if present)
load_dotenv()

app = Flask(__name__)
# Pull secrets from environment; set conservative defaults for local dev
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_super_secret_key')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

# Configure the Gemini API if key is provided in environment
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    else:
        print("GEMINI_API_KEY not set — AI features will be disabled until provided.")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")

# --- Database Helper Function ---
def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Core Routes ---
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', body_class='home-page')

@app.route('/generate', methods=['POST'])
def generate():
    if 'user_id' not in session:
        flash("Please log in to generate an itinerary.", "error")
        return redirect(url_for('login'))

    destination = request.form['destination']
    days = request.form['days']
    trip_type = request.form['trip_type']
    travelers = request.form['travelers']
    budget = request.form['budget']
    
    prompt = f"""
    You are an expert travel planner. Create a detailed travel itinerary and estimate the cost.
    The trip is for {travelers} person(s) to {destination} for {days} days.
    The travel style is {trip_type} with a {budget} budget.

    Provide a detailed day-by-day plan and a rough estimated cost for the entire trip in Indian Rupees (INR).

    IMPORTANT: Respond ONLY with a valid JSON object. The root object must have two keys: "itinerary" and "estimated_cost".
    
    1. The value of "itinerary" must be an array of day-objects.
       - Each day-object must have two keys: "day" (e.g., "Day 1: Arrival") and "plan".
       - The value of "plan" MUST be an array of activity-objects.
       - Each activity-object must have three string keys: "place", "time_to_spend", and "activity".

    2. The value of "estimated_cost" must be a single string (e.g., "₹80,000 - ₹1,20,000 INR for {travelers} people").
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
        response_data = json.loads(cleaned_response_text)

        itinerary = response_data.get('itinerary', [])
        estimated_cost = response_data.get('estimated_cost', 'Not available')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO trips (user_id, destination, days, trip_type, travelers, budget, estimated_cost, itinerary_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (session['user_id'], destination, days, trip_type, travelers, budget, estimated_cost, json.dumps(response_data))
        )
        trip_id = cursor.lastrowid
        conn.commit()
        conn.close()

        unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        image_url = "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1"
        if unsplash_access_key:
            unsplash_url = f"https://api.unsplash.com/search/photos?page=1&query={destination}&client_id={unsplash_access_key}&orientation=landscape"
            try:
                image_response = requests.get(unsplash_url)
                image_response.raise_for_status()
                image_data = image_response.json()
                if image_data['results']:
                    image_url = image_data['results'][0]['urls']['regular']
            except requests.exceptions.RequestException as e:
                print(f"Could not fetch image from Unsplash: {e}")
        
        return render_template('results.html', 
                               trip_id=trip_id,
                               itinerary=itinerary, 
                               destination=destination,
                               days=days,
                               trip_type=trip_type,
                               image_url=image_url,
                               estimated_cost=estimated_cost)

    except Exception as e:
        flash(f"An error occurred. The AI might be busy or the response was malformed. Please try again. Error: {e}", "error")
        return redirect(url_for('index'))


@app.route('/rate-trip/<int:trip_id>', methods=['POST'])
def rate_trip(trip_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401

    data = request.get_json()
    rating = data.get('rating')

    if not rating or not 1 <= rating <= 5:
        return jsonify({'success': False, 'message': 'Invalid rating'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.execute('UPDATE trips SET rating = ? WHERE id = ? AND user_id = ?',
                              (rating, trip_id, session['user_id']))
        conn.commit()
        conn.close()

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Trip not found or permission denied'}), 404
        
        return jsonify({'success': True, 'message': 'Thank you for your feedback!'})
    except Exception as e:
        print(f"Error saving rating: {e}")
        return jsonify({'success': False, 'message': 'An error occurred'}), 500


@app.route('/download-pdf/<int:trip_id>')
def download_pdf(trip_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if HTML is None:
        flash('PDF generation is not available because the server is missing the weasyprint dependency.', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    trip = conn.execute('SELECT * FROM trips WHERE id = ? AND user_id = ?', 
                        (trip_id, session['user_id'])).fetchone()
    conn.close()

    if trip is None:
        flash('Itinerary not found or you do not have permission to access it.', 'error')
        return redirect(url_for('index'))

    itinerary_json = json.loads(trip['itinerary_json'])
    itinerary_data = {
        'itinerary': itinerary_json.get('itinerary', []),
        'destination': trip['destination'],
        'days': trip['days'],
        'trip_type': trip['trip_type'],
        'travelers': trip['travelers'],
        'budget': trip['budget'],
        'estimated_cost': trip['estimated_cost']
    }

    html = render_template('itinerary_pdf.html', **itinerary_data)
    pdf = HTML(string=html).write_pdf()

    return Response(pdf,
                   mimetype='application/pdf',
                   headers={'Content-Disposition': f'attachment; filename=itinerary-{trip["destination"]}.pdf'})


# --- EXPLORE FEATURE ROUTES ---
@app.route('/explore')
def explore():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    categories_to_fetch = [
        {"name": "Beaches", "slug": "beaches", "query": "beach,tropical"},
        {"name": "Mountains", "slug": "mountains", "query": "mountain,peak"},
        {"name": "Vibrant Cities", "slug": "vibrant-cities", "query": "city,night"},
        {"name": "Historical Sites", "slug": "historical-sites", "query": "ancient,ruins"},
        {"name": "Adventure", "slug": "adventure-travel", "query": "adventure,hiking"},
        {"name": "Tropical", "slug": "tropical-paradise", "query": "tropical,island"},
        {"name": "Winter", "slug": "winter-wonderlands", "query": "winter,snow"},
        {"name": "Cultural", "slug": "cultural-hotspots", "query": "culture,festival"}
    ]
    enriched_categories = []
    unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    default_image = "https://placehold.co/800x600/00b4d8/FFFFFF?text=Image+Not+Found"

    for category in categories_to_fetch:
        image_url = default_image
        if unsplash_access_key:
            unsplash_url = f"https://api.unsplash.com/search/photos?page=1&query={category['query']}&client_id={unsplash_access_key}&orientation=landscape"
            try:
                image_response = requests.get(unsplash_url)
                image_response.raise_for_status()
                image_data = image_response.json()
                if image_data['results']:
                    image_url = image_data['results'][0]['urls']['regular']
            except requests.exceptions.RequestException as e:
                print(f"Could not fetch category image for {category['name']} from Unsplash: {e}")
        
        enriched_categories.append({
            "name": category["name"],
            "slug": category["slug"],
            "image_url": image_url
        })

    return render_template('explore.html', categories=enriched_categories, body_class='explore-page')


@app.route('/explore/<category>')
def explore_category(category):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    prompt = f"""
    You are a travel inspiration expert. Generate a list of 8 unique and interesting travel destinations that fit the category: "{category}".
    For each destination, provide a name and a short, one-sentence description.
    Respond ONLY with a valid JSON object with a single root key "destinations".
    """

    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        cleaned_response_text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(cleaned_response_text)
        destinations_from_ai = data.get('destinations', [])

        enriched_destinations = []
        unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
        
        for dest in destinations_from_ai:
            image_url = "https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1"
            if unsplash_access_key:
                unsplash_url = f"https://api.unsplash.com/search/photos?page=1&query=travel {dest['name']}&client_id={unsplash_access_key}&orientation=landscape"
                try:
                    image_response = requests.get(unsplash_url)
                    image_response.raise_for_status()
                    image_data = image_response.json()
                    if image_data['results']:
                        image_url = image_data['results'][0]['urls']['regular']
                except requests.exceptions.RequestException as e:
                    print(f"Could not fetch image for {dest['name']} from Unsplash: {e}")
            
            enriched_destinations.append({
                'name': dest['name'],
                'description': dest['description'],
                'image_url': image_url
            })

        return render_template('destinations.html',
                               category_title=category.replace('-', ' ').title(),
                               destinations=enriched_destinations,
                               body_class='destinations-page')

    except Exception as e:
        flash(f"An error occurred while fetching destinations. Please try again. Error: {e}", "error")
        return redirect(url_for('explore'))


# --- Authentication Routes ---
@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        number = request.form['number']
        username = request.form['username']
        password = request.form['password']
        
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (name, email, number, username, password) VALUES (?, ?, ?, ?, ?)',
                         (name, email, number, username, password_hash))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or Email already exists. Please choose another.', 'error')
        finally:
            conn.close()
    return render_template('register.html', body_class='auth-page')

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Incorrect username or password.', 'error')
            
    return render_template('login.html', body_class='auth-page')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


# --- ADMIN ROUTES ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Incorrect admin password.', 'error')
    # --- THIS IS THE CHANGE ---
    return render_template('admin_login.html', body_class='auth-page', is_admin_page=True)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users ORDER BY name').fetchall()
    conn.close()
    # --- THIS IS THE CHANGE ---
    return render_template('admin_dashboard.html', users=users, body_class='admin-page', is_admin_page=True)

@app.route('/admin/user/<int:user_id>')
def admin_user_trips(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
        
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    trips = conn.execute('SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC', (user_id,)).fetchall()
    conn.close()
    
    if user is None:
        flash('User not found.', 'error')
        return redirect(url_for('admin_dashboard'))
        
    # --- THIS IS THE CHANGE ---
    return render_template('admin_user_trips.html', user=user, trips=trips, body_class='admin-page', is_admin_page=True)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('You have been logged out from the admin panel.', 'success')
    return redirect(url_for('admin_login'))


# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True)
import os
import sqlite3
import random
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# DB file path
DB_PATH = 'movies.db'

def seed_data_if_needed():
    """
    Seeds the database with realistic sample data if it contains 5 or fewer watched movies.
    Ensures that the Pandas analysis and Matplotlib charts are fully populated and meaningful.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if database has tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    if 'watched_movies' not in tables or 'mood_sessions' not in tables:
        # Tables not initialized, let's run db.init_db() or call SQLite directly
        print("Database tables not found. Initializing database schema...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS watched_movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                imdb_id TEXT UNIQUE NOT NULL,
                title TEXT,
                year TEXT,
                poster TEXT,
                genre TEXT,
                rating TEXT,
                plot TEXT,
                watched_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mood_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mood TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        ''')
        conn.commit()

    cursor.execute("SELECT COUNT(*) FROM watched_movies")
    watched_count = cursor.fetchone()[0]
    
    if watched_count > 5:
        conn.close()
        return
        
    print("Database has little or no data. Seeding mock watched movies and mood sessions history...")
    
    # 40 Famous movies to seed with different genres, years, and ratings
    sample_movies = [
        ("tt0111161", "The Shawshank Redemption", "1994", "https://image.url", "Drama", "9.3", "Two imprisoned men bond over a number of years..."),
        ("tt0068646", "The Godfather", "1972", "https://image.url", "Crime, Drama", "9.2", "The aging patriarch of an organized crime dynasty transfers control..."),
        ("tt0468569", "The Dark Knight", "2008", "https://image.url", "Action, Crime, Drama", "9.0", "When the menace known as the Joker wreaks havoc and chaos..."),
        ("tt0137523", "Fight Club", "1999", "https://image.url", "Drama", "8.8", "An insomniac office worker and a devil-may-care soapmaker form..."),
        ("tt0109830", "Forrest Gump", "1994", "https://image.url", "Drama, Romance", "8.8", "The presidencies of Kennedy and Johnson, the Vietnam War..."),
        ("tt1375666", "Inception", "2010", "https://image.url", "Action, Sci-Fi, Adventure", "8.8", "A thief who steals corporate secrets through the use of dream-sharing..."),
        ("tt0110912", "Pulp Fiction", "1994", "https://image.url", "Crime, Drama", "8.9", "The lives of two mob hitmen, a boxer, a gangster and his wife..."),
        ("tt0120737", "The Lord of the Rings: The Fellowship of the Ring", "2001", "https://image.url", "Action, Adventure, Drama, Fantasy", "8.8", "A meek Hobbit from the Shire and eight companions set out on a journey..."),
        ("tt0079590", "Alien", "1979", "https://image.url", "Horror, Sci-Fi", "8.5", "After a space merchant vessel receives an unknown transmission..."),
        ("tt0099785", "Goodfellas", "1990", "https://image.url", "Biography, Crime, Drama", "8.7", "The story of Henry Hill and his life in the mob..."),
        ("tt0087538", "The Karate Kid", "1984", "https://image.url", "Action, Drama, Family", "7.3", "A martial arts master agrees to teach karate to a bullied teen."),
        ("tt0116483", "Happy Gilmore", "1996", "https://image.url", "Comedy, Sport", "7.0", "A rejected hockey player puts his skills to the golf course."),
        ("tt0082971", "Raiders of the Lost Ark", "1981", "https://image.url", "Action, Adventure", "8.4", "In 1936, archaeologist and adventurer Indiana Jones is hired..."),
        ("tt0080684", "Star Wars: Episode V - The Empire Strikes Back", "1980", "https://image.url", "Action, Adventure, Fantasy, Sci-Fi", "8.7", "After the Rebels are brutally overpowered by the Empire..."),
        ("tt0448134", "The Prestige", "2006", "https://image.url", "Drama, Mystery, Sci-Fi", "8.5", "After a tragic accident, two stage magicians engage in a battle..."),
        ("tt0088247", "Terminator 2: Judgment Day", "1991", "https://image.url", "Action, Sci-Fi", "8.6", "A cyborg, identical to the one who failed to kill Sarah Connor..."),
        ("tt0112130", "Toy Story", "1995", "https://image.url", "Animation, Adventure, Comedy", "8.3", "A cowboy doll is profoundly threatened and jealous when a new spaceman..."),
        ("tt0075148", "Rocky", "1976", "https://image.url", "Drama, Sport", "8.1", "A small-time Philadelphia boxer gets a supremely rare chance..."),
        ("tt0114709", "Toy Story 2", "1999", "https://image.url", "Animation, Adventure, Comedy", "7.9", "When Woody is stolen by a toy collector, Buzz Lightyear and his friends..."),
        ("tt0120586", "Princess Mononoke", "1997", "https://image.url", "Animation, Adventure, Fantasy", "8.4", "On a journey to find the cure for a Tatarigami's curse..."),
        ("tt0317505", "Finding Nemo", "2003", "https://image.url", "Animation, Adventure, Comedy, Family", "8.2", "After his son is captured in the Great Barrier Reef and taken..."),
        ("tt0209144", "Memento", "2000", "https://image.url", "Mystery, Thriller", "8.4", "A man with short-term memory loss attempts to track down..."),
        ("tt0110357", "The Lion King", "1994", "https://image.url", "Animation, Adventure, Drama", "8.5", "A young lion prince is cast out of his pride by his cruel uncle..."),
        ("tt0133093", "The Matrix", "1999", "https://image.url", "Action, Sci-Fi", "8.7", "When a beautiful stranger leads computer hacker Neo to a forbidding..."),
        ("tt0172495", "Gladiator", "2000", "https://image.url", "Action, Adventure, Drama", "8.5", "A former Roman General sets out to exact vengeance against..."),
        ("tt0245429", "Spirited Away", "2001", "https://image.url", "Animation, Adventure, Family", "8.6", "During her family's move to the suburbs, a sullen 10-year-old..."),
        ("tt0335266", "Eternal Sunshine of the Spotless Mind", "2004", "https://image.url", "Drama, Romance, Sci-Fi", "8.3", "When their relationship turns sour, a couple undergoes..."),
        ("tt0482571", "Up", "2009", "https://image.url", "Animation, Adventure, Comedy", "8.3", "78-year-old Carl Fredricksen travels to Paradise Falls in his house..."),
        ("tt0816692", "Interstellar", "2014", "https://image.url", "Adventure, Drama, Sci-Fi", "8.7", "When Earth becomes uninhabitable, a team of explorers travels..."),
        ("tt0905372", "Superbad", "2007", "https://image.url", "Comedy", "7.6", "Two co-dependent high school seniors are forced to cope with..."),
        ("tt1130884", "Shutter Island", "2010", "https://image.url", "Mystery, Thriller", "8.2", "Teddy Daniels and Chuck Aule, two US marshals, are sent..."),
        ("tt1205489", "Gran Torino", "2008", "https://image.url", "Drama", "8.1", "Disgruntled Korean War veteran Walt Kowalski sets out to reform..."),
        ("tt1300854", "Iron Man 2", "2010", "https://image.url", "Action, Sci-Fi, Adventure", "6.9", "With the world now aware of his identity as Iron Man..."),
        ("tt2015381", "Guardians of the Galaxy", "2014", "https://image.url", "Action, Adventure, Comedy, Sci-Fi", "8.0", "A group of intergalactic criminals must pull together..."),
        ("tt2256866", "Nightcrawler", "2014", "https://image.url", "Action, Crime, Drama", "7.8", "When Louis Bloom, a con man desperate for work, muscles..."),
        ("tt2582802", "Whiplash", "2014", "https://image.url", "Drama, Music", "8.5", "A promising young drummer enrolls at a cut-throat music academy..."),
        ("tt2975590", "La La Land", "2016", "https://image.url", "Comedy, Drama, Musical", "8.0", "While navigating their careers in Los Angeles, a pianist..."),
        ("tt3316948", "Get Out", "2017", "https://image.url", "Horror, Mystery, Thriller", "7.8", "A young African-American visits his white girlfriend's parents..."),
        ("tt3501632", "Thor: Ragnarok", "2017", "https://image.url", "Action, Adventure, Comedy", "7.9", "Imprisoned on the planet Sakaar, Thor must race against time..."),
        ("tt4154796", "Avengers: Endgame", "2019", "https://image.url", "Action, Adventure, Drama", "8.4", "After the devastating events of Avengers: Infinity War...")
    ]

    base_date = datetime.now() - timedelta(days=120)
    
    # Insert watched movies with random dates in the last 120 days
    for m in sample_movies:
        watched_at = base_date + timedelta(days=random.randint(0, 119), hours=random.randint(0, 23))
        watched_date_str = watched_at.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT OR IGNORE INTO watched_movies 
            (imdb_id, title, year, poster, genre, rating, plot, watched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (m[0], m[1], m[2], m[3], m[4], m[5], m[6], watched_date_str))

    # Seed 100 mood sessions with specific probability weights
    moods = ['happy', 'sad', 'excited', 'scared', 'romantic', 'bored', 'angry', 'nostalgic']
    for _ in range(100):
        mood = random.choices(
            moods, 
            weights=[25, 10, 18, 6, 12, 6, 8, 15], 
            k=1
        )[0]
        
        created_at = base_date + timedelta(days=random.randint(0, 119), hours=random.randint(0, 23))
        created_date_str = created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            INSERT INTO mood_sessions (mood, created_at)
            VALUES (?, ?)
        ''', (mood, created_date_str))
        
    conn.commit()
    conn.close()
    print("Database successfully populated with mock analytics history.")

def run_analysis():
    print("Connecting to database and loading data...")
    conn = sqlite3.connect(DB_PATH)
    df_watched = pd.read_sql_query("SELECT * FROM watched_movies", conn)
    df_moods = pd.read_sql_query("SELECT * FROM mood_sessions", conn)
    conn.close()

    print("\n==============================================")
    print("         MOVIE WATCH HISTORY ANALYSIS         ")
    print("==============================================")

    # 1. Genres Analysis
    # Split comma-separated genres and count frequency
    genres_series = df_watched['genre'].dropna().str.split(', ').explode()
    genre_counts = genres_series.value_counts()
    print("\n--- Top 10 Most Watched Genres ---")
    print(genre_counts.head(10).to_string())

    # 2. Average IMDb Rating
    df_watched['rating_num'] = pd.to_numeric(df_watched['rating'], errors='coerce')
    avg_rating = df_watched['rating_num'].mean()
    print(f"\n--- Average IMDb Rating of Watched Movies: {avg_rating:.2f} / 10 ---")

    # 3. Movies Per Week / Month
    df_watched['watched_at_dt'] = pd.to_datetime(df_watched['watched_at'])
    
    # Calculate time span
    min_date = df_watched['watched_at_dt'].min()
    max_date = df_watched['watched_at_dt'].max()
    days_span = (max_date - min_date).days
    weeks_span = days_span / 7.0 if days_span > 0 else 1.0
    months_span = days_span / 30.4 if days_span > 0 else 1.0
    
    avg_per_week = len(df_watched) / weeks_span
    avg_per_month = len(df_watched) / months_span
    
    print(f"\n--- Watch Frequencies ---")
    print(f"Total Movies Watched: {len(df_watched)}")
    print(f"Time Horizon Spanned: {days_span} days")
    print(f"Average Movies Watched per Week:  {avg_per_week:.2f}")
    print(f"Average Movies Watched per Month: {avg_per_month:.2f}")

    # Movies watched by month
    monthly_watches = df_watched.groupby(df_watched['watched_at_dt'].dt.to_period('M')).size()
    print("\nMovies Watched by Month:")
    print(monthly_watches.to_string())

    # 4. Release Year Distribution
    year_counts = df_watched['year'].value_counts()
    print("\n--- Release Years Watched Most ---")
    print(year_counts.head(5).to_string())


    print("\n==============================================")
    print("            MOOD SESSIONS ANALYSIS            ")
    print("==============================================")

    # 1. Most Picked Mood (Frequency Table)
    mood_counts = df_moods['mood'].value_counts()
    print("\n--- Mood Pick Frequencies ---")
    print(mood_counts.to_string())

    top_mood = mood_counts.idxmax()
    print(f"\nMost Picked Mood: '{top_mood}' (chosen {mood_counts.max()} times)")

    # 2. Usage Day of the Week
    df_moods['created_at_dt'] = pd.to_datetime(df_moods['created_at'])
    df_moods['day_of_week'] = df_moods['created_at_dt'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_counts = df_moods['day_of_week'].value_counts().reindex(day_order).fillna(0).astype(int)
    
    print("\n--- Application Usage by Day of Week ---")
    print(weekday_counts.to_string())
    
    top_day = weekday_counts.idxmax()
    print(f"Most active app usage day: {top_day} ({weekday_counts.max()} sessions)")

    # 3. Mood Trends over Time (Group by Month)
    df_moods['month_period'] = df_moods['created_at_dt'].dt.to_period('M')
    mood_trends_df = df_moods.groupby(['month_period', 'mood']).size().unstack(fill_value=0)
    print("\n--- Mood Trends Over Time (Monthly Pivot) ---")
    print(mood_trends_df.to_string())


    print("\nGenerating dashboard charts and saving to 'dashboard.png'...")
    # MATPLOTLIB VISUALIZATION (Dark Premium Theme)
    plt.style.use('dark_background')
    
    # Custom color palette
    bg_color = '#0D0F14'
    surface_color = '#161920'
    text_color = '#E2E8F0'
    accent_color = '#7C6DFA'
    gold_color = '#F59E0B'
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor(bg_color)
    
    # Chart 1: Top Genres (Horizontal Bar Chart)
    ax_genre = axes[0, 0]
    ax_genre.set_facecolor(surface_color)
    top_genres = genre_counts.head(8)
    bars = ax_genre.barh(top_genres.index, top_genres.values, color=accent_color, edgecolor=border_alpha(accent_color))
    ax_genre.set_title("Most Watched Genres", color=text_color, fontsize=12, fontweight='bold', pad=12)
    ax_genre.invert_yaxis()  # Top genre on top
    ax_genre.tick_params(colors=text_color)
    ax_genre.xaxis.grid(True, linestyle='--', alpha=0.2, color=text_color)
    
    # Chart 2: Mood Frequency (Pie Chart)
    ax_mood = axes[0, 1]
    ax_mood.set_facecolor(surface_color)
    # Define nice colors for each mood
    mood_colors = {
        'happy': '#FAD02C', 'sad': '#3A86C8', 'excited': '#FF6B6B', 'scared': '#7F5A83',
        'romantic': '#FF7597', 'bored': '#8E9AAF', 'angry': '#D90429', 'nostalgic': '#E29578'
    }
    slice_colors = [mood_colors.get(m, '#ffffff') for m in mood_counts.index]
    
    wedges, texts, autotexts = ax_mood.pie(
        mood_counts.values, 
        labels=mood_counts.index, 
        autopct='%1.1f%%', 
        colors=slice_colors,
        wedgeprops=dict(width=0.4, edgecolor='#161920'),  # Donut chart
        startangle=90
    )
    for t in texts:
        t.set_color(text_color)
        t.set_fontsize(9)
    for at in autotexts:
        at.set_color('#000000')
        at.set_fontsize(9)
        at.set_weight('bold')
    ax_mood.set_title("Mood Log Distribution", color=text_color, fontsize=12, fontweight='bold', pad=12)

    # Chart 3: Weekly App Usage (Bar Chart)
    ax_day = axes[1, 0]
    ax_day.set_facecolor(surface_color)
    ax_day.bar(weekday_counts.index, weekday_counts.values, color=gold_color, width=0.6)
    ax_day.set_title("App Usage by Weekday (Mood Logs)", color=text_color, fontsize=12, fontweight='bold', pad=12)
    ax_day.set_xticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
    ax_day.tick_params(colors=text_color)
    ax_day.yaxis.grid(True, linestyle='--', alpha=0.2, color=text_color)

    # Chart 4: Mood Trends Over Time (Stacked Bar Chart)
    ax_trend = axes[1, 1]
    ax_trend.set_facecolor(surface_color)
    
    # We map periods to strings for clean plotting
    mood_trends_df.index = mood_trends_df.index.astype(str)
    
    # Plot stacked bar chart
    mood_trends_df.plot(kind='bar', stacked=True, ax=ax_trend, color=[mood_colors.get(col, '#ffffff') for col in mood_trends_df.columns])
    ax_trend.set_title("Monthly Mood Trends", color=text_color, fontsize=12, fontweight='bold', pad=12)
    ax_trend.tick_params(colors=text_color)
    ax_trend.legend(loc='upper right', bbox_to_anchor=(1, 1), fontsize=8, facecolor=surface_color, edgecolor=text_color)
    plt.xticks(rotation=0)
    ax_trend.yaxis.grid(True, linestyle='--', alpha=0.2, color=text_color)

    plt.tight_layout(pad=3.0)
    plt.savefig('dashboard.png', dpi=150, facecolor=bg_color)
    print("Dashboard saved to 'dashboard.png'.")

def border_alpha(hex_color):
    # Helper to return a slightly lighter border
    return hex_color

if __name__ == '__main__':
    seed_data_if_needed()
    run_analysis()

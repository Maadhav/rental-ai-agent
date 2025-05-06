import sqlite3
import json
import uuid
import datetime
from typing import Dict, List, Union, Optional, Any

class MockDatabase:
    def __init__(self, in_memory=True):
        """Initialize the mock database using SQLite.
        
        Args:
            in_memory (bool): Whether to create an in-memory database (True) or a file-based one (False)
        """
        # Use in-memory SQLite database for simplicity
        if in_memory:
            self.conn = sqlite3.connect(":memory:")
        else:
            self.conn = sqlite3.connect("rental_database.db")
        
        self.cursor = self.conn.cursor()
        
        # Create the necessary tables
        self._create_tables()
        
        # Populate with initial data
        self._populate_initial_data()
    
    def _create_tables(self):
        """Create database tables for apartments, users, amenities, and tours."""
        # Apartments table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS apartments (
            id INTEGER PRIMARY KEY,
            unit_number TEXT NOT NULL,
            apartment_type TEXT NOT NULL,
            floor_plan TEXT,
            square_feet INTEGER,
            bedrooms INTEGER NOT NULL,
            bathrooms REAL NOT NULL,
            rent_amount REAL NOT NULL,
            is_available INTEGER NOT NULL,
            available_date TEXT,
            features TEXT
        )
        ''')
        
        # Users/Prospects table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            user_id TEXT UNIQUE NOT NULL,
            name TEXT,
            phone TEXT,
            email TEXT,
            move_in_date TEXT,
            preferred_apartment_type TEXT,
            has_pets INTEGER,
            income REAL,
            credit_score INTEGER,
            notes TEXT,
            created_at TEXT NOT NULL,
            last_contact TEXT
        )
        ''')
        
        # Property Amenities table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS property_amenities (
            id INTEGER PRIMARY KEY,
            amenity_name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            fee_amount REAL,
            is_included INTEGER NOT NULL
        )
        ''')
        
        # Tours table
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS tours (
            id INTEGER PRIMARY KEY,
            user_id TEXT NOT NULL,
            tour_date TEXT NOT NULL,
            tour_time TEXT NOT NULL,
            apartment_id INTEGER,
            is_virtual INTEGER NOT NULL,
            status TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (apartment_id) REFERENCES apartments (id)
        )
        ''')
        
        # Commit the table creation
        self.conn.commit()
    
    def _populate_initial_data(self):
        """Add initial data to the database tables."""
        # Add apartment units
        apartments_data = [
            # 1-bedroom units
            (101, "101", "1_bedroom", "Maple", 750, 1, 1.0, 1600.0, 1, "2025-07-01", "Corner unit, extra windows"),
            (102, "102", "1_bedroom", "Maple", 750, 1, 1.0, 1600.0, 1, "2025-07-15", "Updated kitchen"),
            (103, "103", "1_bedroom", "Cedar", 780, 1, 1.0, 1650.0, 0, "2025-06-01", "Balcony, park view"),
            (201, "201", "1_bedroom", "Cedar", 780, 1, 1.0, 1650.0, 0, "2025-08-01", "Extra closet space"),
            
            # 2-bedroom units
            (301, "301", "2_bedroom", "Birch", 1050, 2, 2.0, 2100.0, 1, "2025-07-01", "Corner unit, city view"),
            (302, "302", "2_bedroom", "Birch", 1050, 2, 2.0, 2100.0, 1, "2025-07-01", "Updated bathrooms"),
            (401, "401", "2_bedroom", "Aspen", 1100, 2, 2.0, 2200.0, 0, "2025-06-15", "Premium finishes"),
            (402, "402", "2_bedroom", "Aspen", 1100, 2, 2.0, 2200.0, 0, "2025-09-01", "Penthouse floor")
        ]
        
        for apt in apartments_data:
            self.cursor.execute('''
            INSERT INTO apartments (id, unit_number, apartment_type, floor_plan, square_feet, 
                                    bedrooms, bathrooms, rent_amount, is_available, available_date, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', apt)
        
        # Add property amenities
        amenities_data = [
            (1, "Dog-friendly", "Dogs allowed", "Pets", 50.0, 1),
            (2, "Cat-friendly", "Cats allowed", "Pets", 30.0, 1),
            (3, "Fitness Center", "24-hour access fitness center", "Building", 0.0, 1),
            (4, "Pool", "Outdoor pool with sundeck", "Recreation", 0.0, 1),
            (5, "Parking", "Covered parking", "Transportation", 75.0, 0),
            (6, "In-unit Washer/Dryer", "Washer and dryer in each unit", "In-unit", 0.0, 1),
            (7, "Package Lockers", "24-hour package pickup lockers", "Building", 0.0, 1),
            (8, "High-speed Internet", "Fiber internet ready", "Technology", 0.0, 1),
            (9, "Security System", "24-hour security monitoring", "Safety", 0.0, 1),
            (10, "Bike Storage", "Indoor bike storage area", "Transportation", 0.0, 1)
        ]
        
        for amenity in amenities_data:
            self.cursor.execute('''
            INSERT INTO property_amenities (id, amenity_name, description, category, fee_amount, is_included)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', amenity)
        
        # Commit the initial data
        self.conn.commit()
    
    def get_available_apartments(self, apartment_type: Optional[str] = None, 
                                move_in_date: Optional[str] = None) -> List[Dict]:
        """Get available apartments that match the criteria.
        
        Args:
            apartment_type (str, optional): Filter by apartment type (e.g., "1_bedroom", "2_bedroom")
            move_in_date (str, optional): Filter by available date (format: YYYY-MM-DD)
            
        Returns:
            List[Dict]: List of available apartments matching the criteria
        """
        query = "SELECT * FROM apartments WHERE is_available = 1"
        params = []
        
        if apartment_type:
            query += " AND apartment_type = ?"
            params.append(apartment_type)
        
        if move_in_date:
            query += " AND available_date <= ?"
            params.append(move_in_date)
        
        self.cursor.execute(query, params)
        columns = [col[0] for col in self.cursor.description]
        results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
        return results
    
    def get_apartment_by_id(self, apartment_id: int) -> Dict:
        """Get apartment details by ID.
        
        Args:
            apartment_id (int): The apartment ID
            
        Returns:
            Dict: Apartment details or empty dict if not found
        """
        self.cursor.execute("SELECT * FROM apartments WHERE id = ?", (apartment_id,))
        columns = [col[0] for col in self.cursor.description]
        row = self.cursor.fetchone()
        
        if row:
            return dict(zip(columns, row))
        return {}
    
    def get_amenities(self, category: Optional[str] = None) -> List[Dict]:
        """Get property amenities.
        
        Args:
            category (str, optional): Filter amenities by category
            
        Returns:
            List[Dict]: List of amenities
        """
        query = "SELECT * FROM property_amenities"
        params = []
        
        if category:
            query += " WHERE category = ?"
            params.append(category)
        
        self.cursor.execute(query, params)
        columns = [col[0] for col in self.cursor.description]
        results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
        return results
    
    def create_user(self, name: Optional[str] = None, phone: Optional[str] = None, 
                   email: Optional[str] = None, move_in_date: Optional[str] = None,
                   preferred_apartment_type: Optional[str] = None, 
                   has_pets: Optional[bool] = None) -> str:
        """Create a new user/prospect in the database.
        
        Args:
            name (str, optional): User's name
            phone (str, optional): User's phone
            email (str, optional): User's email
            move_in_date (str, optional): User's preferred move-in date
            preferred_apartment_type (str, optional): User's preferred apartment type
            has_pets (bool, optional): Whether user has pets
            
        Returns:
            str: The generated user ID
        """
        user_id = str(uuid.uuid4())
        current_time = datetime.datetime.now().isoformat()
        
        self.cursor.execute('''
        INSERT INTO users (user_id, name, phone, email, move_in_date, preferred_apartment_type,
                          has_pets, created_at, last_contact)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, name, phone, email, move_in_date, preferred_apartment_type, 
              1 if has_pets else 0 if has_pets is not None else None, 
              current_time, current_time))
        
        self.conn.commit()
        return user_id
    
    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user information.
        
        Args:
            user_id (str): The user ID
            **kwargs: Fields to update
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not kwargs:
            return False
            
        # Prepare the SET clause for the SQL UPDATE statement
        set_clause = []
        params = []
        
        for key, value in kwargs.items():
            if key in ['name', 'phone', 'email', 'move_in_date', 'preferred_apartment_type', 
                       'income', 'credit_score', 'notes']:
                set_clause.append(f"{key} = ?")
                params.append(value)
            elif key == 'has_pets' and value is not None:
                set_clause.append("has_pets = ?")
                params.append(1 if value else 0)
        
        if not set_clause:
            return False
            
        # Add last_contact update
        set_clause.append("last_contact = ?")
        params.append(datetime.datetime.now().isoformat())
        
        # Add user_id to params
        params.append(user_id)
        
        self.cursor.execute(f'''
        UPDATE users 
        SET {", ".join(set_clause)}
        WHERE user_id = ?
        ''', params)
        
        self.conn.commit()
        return self.cursor.rowcount > 0
    
    def get_user(self, user_id: str) -> Dict:
        """Get user details by user ID.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            Dict: User details or empty dict if not found
        """
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        columns = [col[0] for col in self.cursor.description]
        row = self.cursor.fetchone()
        
        if row:
            result = dict(zip(columns, row))
            # Convert has_pets from INTEGER to boolean
            if 'has_pets' in result and result['has_pets'] is not None:
                result['has_pets'] = bool(result['has_pets'])
            return result
        return {}
    
    def schedule_tour(self, user_id: str, tour_date: str, tour_time: str, 
                     apartment_id: Optional[int] = None, is_virtual: bool = False, 
                     notes: Optional[str] = None) -> int:
        """Schedule a property tour.
        
        Args:
            user_id (str): The user ID
            tour_date (str): Tour date (format: YYYY-MM-DD)
            tour_time (str): Tour time (format: HH:MM)
            apartment_id (int, optional): Specific apartment to tour
            is_virtual (bool): Whether the tour is virtual
            notes (str, optional): Additional notes
            
        Returns:
            int: The tour ID or -1 if failed
        """
        try:
            self.cursor.execute('''
            INSERT INTO tours (user_id, tour_date, tour_time, apartment_id, is_virtual, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, tour_date, tour_time, apartment_id, 1 if is_virtual else 0, 
                 "Scheduled", notes))
            
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"Error scheduling tour: {e}")
            return -1
    
    def get_user_tours(self, user_id: str) -> List[Dict]:
        """Get all tours scheduled for a user.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            List[Dict]: List of scheduled tours
        """
        self.cursor.execute('''
        SELECT t.*, a.unit_number, a.apartment_type, a.floor_plan
        FROM tours t
        LEFT JOIN apartments a ON t.apartment_id = a.id
        WHERE t.user_id = ?
        ORDER BY t.tour_date, t.tour_time
        ''', (user_id,))
        
        columns = [col[0] for col in self.cursor.description]
        results = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
        # Convert is_virtual from INTEGER to boolean
        for result in results:
            if 'is_virtual' in result:
                result['is_virtual'] = bool(result['is_virtual'])
                
        return results
    
    def get_pricing_info(self, apartment_type: Optional[str] = None) -> Dict:
        """Get pricing information for apartments.
        
        Args:
            apartment_type (str, optional): Filter by apartment type
            
        Returns:
            Dict: Pricing information
        """
        query = '''
        SELECT apartment_type, 
               MIN(rent_amount) as min_rent, 
               MAX(rent_amount) as max_rent,
               AVG(rent_amount) as avg_rent,
               COUNT(*) as count
        FROM apartments
        '''
        
        params = []
        if apartment_type:
            query += " WHERE apartment_type = ?"
            params.append(apartment_type)
        
        query += " GROUP BY apartment_type"
        
        self.cursor.execute(query, params)
        results = {}
        
        for row in self.cursor.fetchall():
            apt_type, min_rent, max_rent, avg_rent, count = row
            results[apt_type] = {
                "min_rent": min_rent,
                "max_rent": max_rent,
                "avg_rent": avg_rent,
                "count": count
            }
        
        return results
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
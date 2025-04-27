import sqlite3
import os
from datetime import datetime

DATABASE_NAME = 'donor_management.db'

# --- Database Setup ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
    conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
    return conn

def create_tables(conn):
    """Creates the necessary database tables if they don't exist."""
    cursor = conn.cursor()
    try:
        # Donors Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Donors (
                donor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')

        # Volunteers Table (Optional, for linking donations)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Volunteers (
                volunteer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, -- Assuming volunteer names are unique for simplicity
                contact_info TEXT
            );
        ''')

        # Events Table (Optional, for linking donations)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, -- Assuming event names are unique
                event_date TEXT -- Store dates as text (YYYY-MM-DD) or use REAL for Julian day
            );
        ''')

        # Donations Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Donations (
                donation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK(amount > 0), -- Ensure positive donation amount
                donation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                volunteer_id INTEGER, -- Optional link
                event_id INTEGER,     -- Optional link
                notes TEXT,           -- Optional notes about the donation
                FOREIGN KEY (donor_id) REFERENCES Donors(donor_id) ON DELETE CASCADE, -- If donor is deleted, delete their donations
                FOREIGN KEY (volunteer_id) REFERENCES Volunteers(volunteer_id) ON DELETE SET NULL, -- If volunteer deleted, set FK to NULL
                FOREIGN KEY (event_id) REFERENCES Events(event_id) ON DELETE SET NULL -- If event deleted, set FK to NULL
            );
        ''')
        conn.commit()
        print("Database tables checked/created successfully.")
    except sqlite3.Error as e:
        print(f"Error creating tables: {e}")
        conn.rollback()

def find_id_by_name(conn, table_name, column_name, name_value):
    """Finds the ID of a record by its name in a given table."""
    cursor = conn.cursor()
    try:
        query = f"SELECT {column_name}_id FROM {table_name} WHERE LOWER(name) = LOWER(?)"
        cursor.execute(query, (name_value,))
        result = cursor.fetchone()
        return result[f'{column_name}_id'] if result else None
    except sqlite3.Error as e:
        print(f"Error finding ID in {table_name} by name: {e}")
        return None

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def display_results(rows, title="Results"):
    """Displays query results in a formatted way."""
    if not rows:
        print(f"\n--- No {title.lower()} found. ---")
        return

    print(f"\n--- {title} ---")

    if rows:
        headers = rows[0].keys()
        print(" | ".join(headers))
        print("-" * (sum(len(h) for h in headers) + 3 * (len(headers) - 1)))
        for row in rows:
            print(" | ".join(map(str, row)))
    print("---------------")

def add_donor(conn):
    """Adds a new donor to the database."""
    print("\n--- Add New Donor ---")
    name = input("Enter donor name: ").strip()
    contact_info = input("Enter contact info (e.g., email/phone): ").strip()

    if not name:
        print("Donor name cannot be empty.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Donors (name, contact_info) VALUES (?, ?)", (name, contact_info))
        conn.commit()
        print(f"Donor '{name}' added successfully (ID: {cursor.lastrowid}).")
    except sqlite3.IntegrityError:
         print(f"Error: A donor with a similar unique constraint might already exist.")
    except sqlite3.Error as e:
        print(f"Error adding donor: {e}")
        conn.rollback()

def view_donors(conn):
    """Views all donors in the database."""
    print("\n--- View All Donors ---")
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT donor_id, name, contact_info, created_at FROM Donors ORDER BY name")
        donors = cursor.fetchall()
        display_results(donors, "All Donors")
    except sqlite3.Error as e:
        print(f"Error viewing donors: {e}")

def update_donor(conn):
    """Updates an existing donor's information."""
    print("\n--- Update Donor ---")
    try:
        donor_id = int(input("Enter the ID of the donor to update: "))
    except ValueError:
        print("Invalid ID. Please enter a number.")
        return

    cursor = conn.cursor()
    # Check if donor exists
    cursor.execute("SELECT name, contact_info FROM Donors WHERE donor_id = ?", (donor_id,))
    donor = cursor.fetchone()

    if not donor:
        print(f"Donor with ID {donor_id} not found.")
        return

    print(f"Updating Donor ID: {donor_id}, Current Name: {donor['name']}, Current Contact: {donor['contact_info']}")
    new_name = input(f"Enter new name (leave blank to keep '{donor['name']}'): ").strip()
    new_contact_info = input(f"Enter new contact info (leave blank to keep '{donor['contact_info']}'): ").strip()

    update_fields = {}
    if new_name:
        update_fields['name'] = new_name
    if new_contact_info:
        update_fields['contact_info'] = new_contact_info

    if not update_fields:
        print("No changes specified.")
        return

    set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
    values = list(update_fields.values())
    values.append(donor_id)

    try:
        cursor.execute(f"UPDATE Donors SET {set_clause} WHERE donor_id = ?", tuple(values))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Donor ID {donor_id} updated successfully.")
        else:
             print(f"Donor ID {donor_id} not found or no changes made.") # Should not happen due to check above, but good practice
    except sqlite3.Error as e:
        print(f"Error updating donor: {e}")
        conn.rollback()

def delete_donor(conn):
    """Deletes a donor from the database."""
    print("\n--- Delete Donor ---")
    try:
        donor_id = int(input("Enter the ID of the donor to delete: "))
    except ValueError:
        print("Invalid ID. Please enter a number.")
        return

    cursor = conn.cursor()
    # Optional: Confirm deletion
    cursor.execute("SELECT name FROM Donors WHERE donor_id = ?", (donor_id,))
    donor = cursor.fetchone()
    if not donor:
        print(f"Donor with ID {donor_id} not found.")
        return

    confirm = input(f"Are you sure you want to delete donor '{donor['name']}' (ID: {donor_id})? This will also delete associated donations. (yes/no): ").lower()
    if confirm != 'yes':
        print("Deletion cancelled.")
        return

    try:
        cursor.execute("DELETE FROM Donors WHERE donor_id = ?", (donor_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Donor ID {donor_id} and associated donations deleted successfully.")
        else:
            print(f"Donor ID {donor_id} not found.")
    except sqlite3.Error as e:
        print(f"Error deleting donor: {e}")
        conn.rollback()



def add_volunteer(conn):
    """Adds a new volunteer."""
    print("\n--- Add New Volunteer ---")
    name = input("Enter volunteer name: ").strip()
    contact_info = input("Enter contact info (optional): ").strip()
    if not name:
        print("Volunteer name cannot be empty.")
        return
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Volunteers (name, contact_info) VALUES (?, ?)", (name, contact_info))
        conn.commit()
        print(f"Volunteer '{name}' added successfully (ID: {cursor.lastrowid}).")
    except sqlite3.IntegrityError:
         print(f"Error: A volunteer with the name '{name}' might already exist (names must be unique).")
    except sqlite3.Error as e:
        print(f"Error adding volunteer: {e}")
        conn.rollback()

def add_event(conn):
    """Adds a new event."""
    print("\n--- Add New Event ---")
    name = input("Enter event name: ").strip()
    event_date_str = input("Enter event date (YYYY-MM-DD, optional): ").strip()
    if not name:
        print("Event name cannot be empty.")
        return
    # Basic date validation (optional but recommended)
    if event_date_str:
        try:
            datetime.strptime(event_date_str, '%Y-%m-%d')
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
            return
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Events (name, event_date) VALUES (?, ?)", (name, event_date_str if event_date_str else None))
        conn.commit()
        print(f"Event '{name}' added successfully (ID: {cursor.lastrowid}).")
    except sqlite3.IntegrityError:
         print(f"Error: An event with the name '{name}' might already exist (names must be unique).")
    except sqlite3.Error as e:
        print(f"Error adding event: {e}")
        conn.rollback()

# --- Donation Operations ---

def add_donation(conn):
    """Adds a new donation record."""
    print("\n--- Add New Donation ---")
    donor_name = input("Enter the donor's name: ").strip()
    donor_id = find_id_by_name(conn, "Donors", "donor", donor_name)

    if donor_id is None:
        print(f"Donor '{donor_name}' not found. Please add the donor first.")
        return

    try:
        amount = float(input("Enter donation amount: "))
        if amount <= 0:
            print("Donation amount must be positive.")
            return
    except ValueError:
        print("Invalid amount. Please enter a number.")
        return

    donation_date_str = input("Enter donation date (YYYY-MM-DD HH:MM:SS, leave blank for current time): ").strip()
    if donation_date_str:
        try:

            datetime.strptime(donation_date_str, '%Y-%m-%d %H:%M:%S')
            donation_date = donation_date_str
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD HH:MM:SS.")
            return
    else:
        donation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S') # Use current time if blank


    volunteer_name = input("Enter volunteer name (leave blank if none): ").strip()
    volunteer_id = find_id_by_name(conn, "Volunteers", "volunteer", volunteer_name) if volunteer_name else None
    if volunteer_name and volunteer_id is None:
        print(f"Warning: Volunteer '{volunteer_name}' not found. Donation will be added without volunteer link.")

    event_name = input("Enter event name (leave blank if none): ").strip()
    event_id = find_id_by_name(conn, "Events", "event", event_name) if event_name else None
    if event_name and event_id is None:
        print(f"Warning: Event '{event_name}' not found. Donation will be added without event link.")

    notes = input("Enter any notes for this donation (optional): ").strip()

    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO Donations (donor_id, amount, donation_date, volunteer_id, event_id, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (donor_id, amount, donation_date, volunteer_id, event_id, notes))
        conn.commit()
        print(f"Donation of ${amount:.2f} from '{donor_name}' recorded successfully (ID: {cursor.lastrowid}).")
    except sqlite3.Error as e:
        print(f"Error adding donation: {e}")
        conn.rollback()



def search_donations(conn):
    """Provides options to search donations."""
    print("\n--- Search Donations ---")
    print("Search by:")
    print("1. Donor Name")
    print("2. Volunteer Name")
    print("3. Event Name")
    choice = input("Enter your choice (1-3): ")

    search_term = input("Enter the name to search for: ").strip()
    if not search_term:
        print("Search term cannot be empty.")
        return

    cursor = conn.cursor()
    query = """
        SELECT
            d.donation_id,
            dn.name AS donor_name,
            d.amount,
            d.donation_date,
            v.name AS volunteer_name,
            e.name AS event_name,
            d.notes
        FROM Donations d
        JOIN Donors dn ON d.donor_id = dn.donor_id
        LEFT JOIN Volunteers v ON d.volunteer_id = v.volunteer_id
        LEFT JOIN Events e ON d.event_id = e.event_id
    """
    params = (f"%{search_term}%",)

    try:
        if choice == '1':
            query += " WHERE LOWER(dn.name) LIKE LOWER(?)"
            title = f"Donations by Donor matching '{search_term}'"
        elif choice == '2':
            query += " WHERE LOWER(v.name) LIKE LOWER(?)"
            title = f"Donations by Volunteer matching '{search_term}'"
        elif choice == '3':
            query += " WHERE LOWER(e.name) LIKE LOWER(?)"
            title = f"Donations by Event matching '{search_term}'"
        else:
            print("Invalid choice.")
            return

        query += " ORDER BY d.donation_date DESC"
        cursor.execute(query, params)
        results = cursor.fetchall()
        display_results(results, title)

    except sqlite3.Error as e:
        print(f"Error searching donations: {e}")




def display_menu():
    """Displays the main menu options."""
    print("\n--- Donor Management Menu ---")
    print("1. Add Donor")
    print("2. View All Donors")
    print("3. Update Donor")
    print("4. Delete Donor")
    print("---------------------------")
    print("5. Add Volunteer")
    print("6. Add Event")
    print("---------------------------")
    print("7. Add Donation")
    print("8. Search Donations")
    print("---------------------------")
    print("0. Exit")
    print("---------------------------")

def main():
    """Main function to run the application."""
    conn = get_db_connection()
    create_tables(conn)

    while True:
        clear_screen()
        display_menu()
        choice = input("Enter your choice: ")

        clear_screen()

        if choice == '1':
            add_donor(conn)
        elif choice == '2':
            view_donors(conn)
        elif choice == '3':
            update_donor(conn)
        elif choice == '4':
            delete_donor(conn)
        elif choice == '5':
            add_volunteer(conn)
        elif choice == '6':
            add_event(conn)
        elif choice == '7':
            add_donation(conn)
        elif choice == '8':
            search_donations(conn)
        elif choice == '0':
            print("Exiting application.")
            break
        else:
            print("Invalid choice. Please try again.")

        input("\nPress Enter to continue...")

    conn.close()

if __name__ == "__main__":
    main()

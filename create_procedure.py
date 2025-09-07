#!/usr/bin/env python3

import pymysql
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root') 
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'sahilmon_padho')

def create_stored_procedure():
    try:
        # Connect to database
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        
        print(f"Connected to database: {DB_NAME}")
        
        # Read the SQL file
        with open('missing_course_procedures.sql', 'r', encoding='utf-8') as file:
            sql_content = file.read()
        
        # Split by procedure definitions and execute the usp_GetCoursesPublic procedure only
        procedures = sql_content.split('-- 6. Get Courses for Public Access with Advanced Filtering')[1]
        procedures = procedures.split('-- ')[0]  # Get only the first procedure after the comment
        
        with connection.cursor() as cursor:
            # Execute the procedure creation
            print("Creating usp_GetCoursesPublic stored procedure...")
            cursor.execute(procedures)
            connection.commit()
            print("✅ usp_GetCoursesPublic procedure created successfully!")
            
        # Test the procedure
        with connection.cursor() as cursor:
            print("\nTesting the procedure with basic parameters...")
            cursor.callproc('usp_GetCoursesPublic', [
                None,      # p_course_id
                None,      # p_search
                None,      # p_category_id  
                'created_at',  # p_sort_by
                'desc',    # p_sort_order
                5,         # p_limit
                0,         # p_offset
                None,      # p_min_price
                None,      # p_max_price
                'active'   # p_status
            ])
            
            results = cursor.fetchall()
            print(f"✅ Procedure test successful! Found {len(results)} courses")
            
            if results:
                print("\nSample course:")
                for key, value in list(results[0].items())[:5]:  # Show first 5 fields
                    print(f"  {key}: {value}")
                    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    finally:
        if 'connection' in locals():
            connection.close()
            print("Database connection closed.")
    
    return True

if __name__ == "__main__":
    print("=== Creating usp_GetCoursesPublic Stored Procedure ===")
    success = create_stored_procedure()
    
    if success:
        print("\n🎉 Procedure creation completed successfully!")
        print("You can now use the /api/course/public endpoint.")
    else:
        print("\n💥 Procedure creation failed!")

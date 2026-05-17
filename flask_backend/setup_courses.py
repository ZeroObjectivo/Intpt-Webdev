import os
import sys
from dotenv import load_dotenv

# Add the current directory to sys.path to import services
sys.path.append(os.path.join(os.getcwd(), 'flask_backend'))
load_dotenv(os.path.join(os.getcwd(), 'flask_backend', '.env'))

try:
    from flask_backend.services.supabase_client import supabase_service
except ImportError:
    from services.supabase_client import supabase_service

def setup_courses():
    print("Starting course and college synchronization...")
    
    # 1. Update/Sync Colleges & Institutes
    colleges_data = [
        {"name": "CCAPS", "full_name": "College of Continuing, Advanced and Professional Studies", "type": "College"},
        {"name": "CBFS", "full_name": "College of Business and Financial Sciences", "type": "College"},
        {"name": "CCIS", "full_name": "College of Computing and Information Sciences", "type": "College"},
        {"name": "CCSE", "full_name": "College of Construction Sciences and Engineering", "type": "College"},
        {"name": "CHK", "full_name": "College of Human Kinetics", "type": "College"},
        {"name": "CGPP", "full_name": "College of Governance and Public Policy", "type": "College"},
        {"name": "CITE", "full_name": "College of Innovative Teacher Education", "type": "College"},
        {"name": "CTHM", "full_name": "College of Tourism and Hospitality Management", "type": "College"},
        {"name": "CET", "full_name": "College of Engineering Technology", "type": "College"},
        {"name": "HSU", "full_name": "Higher School ng UMak", "type": "College"},
        {"name": "SOL", "full_name": "School of Law", "type": "Institute"},
        {"name": "IAD", "full_name": "Institute of Arts and Design", "type": "Institute"},
        {"name": "IOA", "full_name": "Institute of Accountancy", "type": "Institute"},
        {"name": "IOP", "full_name": "Institute of Pharmacy", "type": "Institute"},
        {"name": "ION", "full_name": "Institute of Nursing", "type": "Institute"},
        {"name": "IIHS", "full_name": "Institute of Imaging Health Sciences", "type": "Institute"},
        {"name": "IOPsy", "full_name": "Institute of Psychology", "type": "Institute"},
        {"name": "IDEM", "full_name": "Institute for Disaster and Emergency Management", "type": "Institute"},
        {"name": "ISW", "full_name": "Institute for Social Work", "type": "Institute"},
    ]

    for col in colleges_data:
        res = supabase_service.table('colleges_institutes').upsert(col, on_conflict='name').execute()
        if res.data:
            print(f"Synced college: {col['name']}")

    # Get the latest mapping of name -> id
    colleges_res = supabase_service.table('colleges_institutes').select('id, name').execute()
    col_map = {item['name']: item['id'] for item in colleges_res.data}

    # 2. Define Courses
    courses_data = [
        # CCAPS
        {"col": "CCAPS", "name": "BA in Political Science major in LGA", "type": "Undergraduate"},
        {"col": "CCAPS", "name": "Bachelor in Automotive Technology", "type": "Undergraduate"},
        {"col": "CCAPS", "name": "Bachelor in Industrial Facilities Tech Mgmt", "type": "Undergraduate"},
        {"col": "CCAPS", "name": "BSBA major in HRDM", "type": "Undergraduate"},
        {"col": "CCAPS", "name": "BS in Entrepreneurship", "type": "Undergraduate"},
        {"col": "CCAPS", "name": "Certificate in Barangay Governance", "type": "Certificate"},
        {"col": "CCAPS", "name": "Diploma in Development Mgmt and Governance", "type": "Diploma"},
        {"col": "CCAPS", "name": "MA in Education (Admin/Guidance)", "type": "Masters"},
        {"col": "CCAPS", "name": "MA in Innovative Education", "type": "Masters"},
        {"col": "CCAPS", "name": "Master in Business Administration", "type": "Masters"},
        {"col": "CCAPS", "name": "Master in Public Administration", "type": "Masters"},
        {"col": "CCAPS", "name": "Doctor of Education", "type": "Doctorate"},
        {"col": "CCAPS", "name": "PhD in Leadership", "type": "Doctorate"},
        
        # IAD
        {"col": "IAD", "name": "Bachelor in Multimedia Arts", "type": "Undergraduate"},
        {"col": "IAD", "name": "Associate in Customer Service Communication", "type": "Associate"},
        
        # CBFS
        {"col": "CBFS", "name": "BSBA major in Building and Property Mgmt", "type": "Undergraduate"},
        {"col": "CBFS", "name": "BSBA major in Supply Management", "type": "Undergraduate"},
        {"col": "CBFS", "name": "BS in Entrepreneurial Management", "type": "Undergraduate"},
        {"col": "CBFS", "name": "BSBA major in Marketing Management", "type": "Undergraduate"},
        {"col": "CBFS", "name": "BS in Office Administration", "type": "Undergraduate"},
        {"col": "CBFS", "name": "BSBA major in Human Resource Management", "type": "Undergraduate"},
        {"col": "CBFS", "name": "BS in Financial Management", "type": "Undergraduate"},
        {"col": "CBFS", "name": "Associate in Supply Management", "type": "Associate"},
        
        # IOA
        {"col": "IOA", "name": "BS in Accountancy (BSA)", "type": "Undergraduate"},
        {"col": "IOA", "name": "BS in Management Accounting (BSMA)", "type": "Undergraduate"},
        
        # CCIS
        {"col": "CCIS", "name": "BS in Computer Science", "type": "Undergraduate"},
        {"col": "CCIS", "name": "BS in Information Technology", "type": "Undergraduate"},
        {"col": "CCIS", "name": "Diploma in Application Development", "type": "Diploma"},
        {"col": "CCIS", "name": "Diploma in Computer Network Administration", "type": "Diploma"},
        
        # CCSE
        {"col": "CCSE", "name": "BS in Civil Engineering", "type": "Undergraduate"},
        
        # CHK
        {"col": "CHK", "name": "BS in Exercise and Sports Science", "type": "Undergraduate"},
        
        # CGPP
        {"col": "CGPP", "name": "BA in Political Science major in Paralegal", "type": "Undergraduate"},
        {"col": "CGPP", "name": "BA in Political Science major in Policy Mgmt", "type": "Undergraduate"},
        {"col": "CGPP", "name": "BA in Political Science major in LGA", "type": "Undergraduate"},
        
        # ION
        {"col": "ION", "name": "BS in Nursing", "type": "Undergraduate"},
        {"col": "ION", "name": "Master of Arts in Nursing", "type": "Masters"},
        
        # IOP
        {"col": "IOP", "name": "BS in Pharmacy", "type": "Undergraduate"},
        {"col": "IOP", "name": "Associate in Applied Science in Pharmacy Tech", "type": "Associate"},
        
        # IIHS
        {"col": "IIHS", "name": "BS in Radiologic Technology", "type": "Undergraduate"},
        {"col": "IIHS", "name": "MS in Radiologic Technology", "type": "Masters"},
        
        # CITE
        {"col": "CITE", "name": "Bachelor of Elementary Education", "type": "Undergraduate"},
        {"col": "CITE", "name": "BSE major in English", "type": "Undergraduate"},
        {"col": "CITE", "name": "BSE major in Mathematics", "type": "Undergraduate"},
        {"col": "CITE", "name": "BSE major in Social Studies", "type": "Undergraduate"},
        
        # IOPsy
        {"col": "IOPsy", "name": "BS in Psychology", "type": "Undergraduate"},
        
        # CTHM
        {"col": "CTHM", "name": "BS in Hospitality Management", "type": "Undergraduate"},
        {"col": "CTHM", "name": "BS in Tourism Management", "type": "Undergraduate"},
        {"col": "CTHM", "name": "Associate in Hospitality Management", "type": "Associate"},
        
        # IDEM
        {"col": "IDEM", "name": "BS in Disaster Risk Management (BSDRM)", "type": "Undergraduate"},
        
        # ISW
        {"col": "ISW", "name": "BS in Social Work (BSSW)", "type": "Undergraduate"},
        
        # CET
        {"col": "CET", "name": "BET major in Electrical Technology", "type": "Undergraduate"},
        {"col": "CET", "name": "BET major in Electronics Technology", "type": "Undergraduate"},
        {"col": "CET", "name": "Bachelor in Automotive Technology", "type": "Undergraduate"},
        {"col": "CET", "name": "Diploma in Industrial Facilities Technology", "type": "Diploma"},
        
        # SOL
        {"col": "SOL", "name": "Juris Doctor with Thesis", "type": "Graduate"},
        
        # HSU
        {"col": "HSU", "name": "Automotive Servicing", "type": "TVL"},
        {"col": "HSU", "name": "Drafting Technology", "type": "TVL"},
        {"col": "HSU", "name": "Computer Programming", "type": "TVL"},
        {"col": "HSU", "name": "Computer Systems Servicing", "type": "TVL"},
        {"col": "HSU", "name": "Music", "type": "Arts & Design"},
        {"col": "HSU", "name": "Film Production", "type": "Arts & Design"},
        {"col": "HSU", "name": "Visual Arts and Multimedia Arts", "type": "Arts & Design"},
        {"col": "HSU", "name": "Sports Coaching", "type": "Sports"},
    ]

    # Clear existing courses first to avoid duplicates or orphans during this sync
    supabase_service.table('courses').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()

    to_insert = []
    for item in courses_data:
        college_id = col_map.get(item['col'])
        if college_id:
            to_insert.append({
                "college_id": college_id,
                "name": item['name'],
                "program_type": item['type']
            })

    if to_insert:
        # Insert in batches of 50
        for i in range(0, len(to_insert), 50):
            batch = to_insert[i:i+50]
            supabase_service.table('courses').insert(batch).execute()
        print(f"Successfully inserted {len(to_insert)} courses.")
    else:
        print("No courses to insert.")

if __name__ == "__main__":
    setup_courses()

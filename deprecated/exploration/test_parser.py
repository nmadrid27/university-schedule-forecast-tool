import re
import os

from utils import get_data_dir

masterlist_path = os.path.join(get_data_dir(), "Masterlist.md")

def parse_masterlist(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    
    mapping = {}
    current_major = None
    in_first_year = False
    
    for line in lines:
        line = line.strip()
        # Detect Major Header: "## MAJOR NAME"
        if line.startswith("## ") and not line.startswith("###"):
            current_major = line[3:].strip()
            # Clean up modifiers like "Group A"
            if "Group" in current_major:
                current_major = current_major.split("Group")[0].strip()
            # Clean up "Fall Only..."
            if "Fall Only" in current_major:
                 # extract the part after Only
                 pass # simplified for now
            mapping[current_major] = []
            in_first_year = False
        
        # Detect First Year Section
        if line.startswith("#### First Year"):
            in_first_year = True
        elif line.startswith("#### Second Year"):
            in_first_year = False
            
        # Detect Course
        if in_first_year and line.startswith("- FOUN"):
            # Extract FOUN XXX
            match = re.search(r'(FOUN \d{3})', line)
            if match:
                course = match.group(1)
                if current_major:
                    mapping[current_major].append(course)

    # Print a few samples
    print(f"Found {len(mapping)} majors.")
    for m in list(mapping.keys())[:5]:
        print(f"{m}: {mapping[m]}")

parse_masterlist(masterlist_path)

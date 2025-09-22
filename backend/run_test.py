import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("SUPABASE_URL:", os.getenv('SUPABASE_URL'))
print("Has ANON_KEY:", bool(os.getenv('SUPABASE_ANON_KEY')))

# Now import and run the test
if os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'):
    print("Environment loaded successfully!")
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/integration/test_access_control.py::test_anonymous_cannot_create_projects", 
        "-v", "-s"
    ], capture_output=True, text=True)
    
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    print("Return code:", result.returncode)
else:
    print("Environment variables not loaded correctly")

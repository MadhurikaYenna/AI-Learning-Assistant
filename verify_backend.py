import os
import sys

def run_tests():
    print("="*50)
    print("RUNNING SYSTEM DIAGNOSTICS & VERIFICATION TESTS")
    print("="*50)
    
    # Test 1: Check Imports
    print("Test 1: Importing backend modules...", end=" ")
    try:
        import db_helpers
        import auth_helpers
        import models_helpers
        import rag_helpers
        import playground_helpers
        import interview_helpers
        import voice_helpers
        import subscription_helpers
        import analytics_helpers
        print("PASS")
    except Exception as e:
        print("FAIL")
        print(f"Error importing modules: {e}")
        sys.exit(1)
        
    # Test 2: Database Initialization
    print("Test 2: Initializing SQLite database schema...", end=" ")
    try:
        db_helpers.init_db()
        # Verify db file is created
        db_path = db_helpers.DB_FILE
        if os.path.exists(db_path):
            print(f"PASS (Created at {db_path})")
        else:
            print("FAIL (DB file not found)")
            sys.exit(1)
    except Exception as e:
        print(f"FAIL (DB init crashed: {e})")
        sys.exit(1)
        
    # Test 3: Authentication & Hashing
    print("Test 3: Testing password hashing & verification...", end=" ")
    try:
        pwd = "TestPassword123"
        hashed = auth_helpers.hash_password(pwd)
        assert hashed != pwd, "Hash cannot match plain password"
        assert auth_helpers.verify_password(pwd, hashed) == True, "Verification failed for correct password"
        assert auth_helpers.verify_password("WrongPassword", hashed) == False, "Verification passed for incorrect password"
        print("PASS")
    except Exception as e:
        print(f"FAIL (Password test failed: {e})")
        sys.exit(1)
        
    # Test 4: Code Execution Sandbox
    print("Test 4: Testing subprocess playground execution sandbox...", end=" ")
    try:
        # Test Python script
        stdout_py, stderr_py, code_py = playground_helpers.run_code_safely("python", "print('Python OK')")
        assert code_py == 0, f"Python execution failed: {stderr_py}"
        assert stdout_py.strip() == "Python OK", f"Python output mismatch: {stdout_py}"
        
        # Test JS script
        stdout_js, stderr_js, code_js = playground_helpers.run_code_safely("javascript", "console.log('JS OK')")
        assert code_js == 0, f"JS execution failed: {stderr_js}"
        assert stdout_js.strip() == "JS OK", f"JS output mismatch: {stdout_js}"
        
        print("PASS")
    except Exception as e:
        print(f"FAIL (Sandbox test failed: {e})")
        sys.exit(1)
        
    print("="*50)
    print("ALL TESTS PASSED! APPLICATION IS READY FOR DEPLOYMENT.")
    print("="*50)

if __name__ == "__main__":
    run_tests()

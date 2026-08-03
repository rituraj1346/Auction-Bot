import os
import sys
import time
import subprocess

# Hardcode the root directory to ensure paths always resolve correctly
PROJECT_ROOT = r"D:\AuctionBot"

def run_master_pipeline():
    # Change the working directory to the project root
    os.chdir(PROJECT_ROOT)
    
    print("====================================================")
    print("     [1/2] FIRING AGGRESSIVE OTP TRIGGER")
    print("====================================================")
    
    # sys.executable ensures it uses your exact Python environment
    otp_script_path = os.path.join("scrapers", "ireps_otp_trigger.py")
    subprocess.run([sys.executable, otp_script_path])
    
    print("\n[WAIT] Giving Gmail 45 seconds to receive and sync the OTP...")
    time.sleep(45)

    print("\n====================================================")
    print("     [2/2] LAUNCHING MAIN IREPS ENGINE")
    print("====================================================")
    
    main_script_path = "run_ireps.py"
    subprocess.run([sys.executable, main_script_path])
    
    print("\n✅ ALL AUTOMATION PIPELINES COMPLETED!")

if __name__ == "__main__":
    run_master_pipeline()
#!/usr/bin/env python3
"""
Debug the global monitoring setup
"""

print("=== DEBUGGING GLOBAL MONITORING ===")

# First check if LLMUtils can be imported
try:
    from llm_utils import LLMUtils
    print("✅ LLMUtils imported successfully")
    
    # Check if _monitor_instance exists
    if hasattr(LLMUtils, '_monitor_instance'):
        print("✅ LLMUtils._monitor_instance attribute exists")
        
        if LLMUtils._monitor_instance is not None:
            print("✅ LLMUtils._monitor_instance is not None")
            print(f"Monitor instance type: {type(LLMUtils._monitor_instance)}")
            
            # Test if we can call methods on it
            try:
                total_calls = LLMUtils._monitor_instance.db.get_total_calls()
                print(f"✅ Monitor working - Total calls in DB: {total_calls}")
            except Exception as e:
                print(f"❌ Monitor instance error: {e}")
        else:
            print("❌ LLMUtils._monitor_instance is None")
    else:
        print("❌ LLMUtils._monitor_instance attribute does not exist")
        
except Exception as e:
    print(f"❌ Error importing LLMUtils: {e}")

print("\n=== TESTING DIRECT MONITORING ===")

# Try to create a monitoring instance directly
try:
    from master_monitoring import MasterMonitoring
    monitor = MasterMonitoring()
    print("✅ Direct MasterMonitoring instance created")
    
    # Test recording an API call
    monitor.record_api_call(
        model="gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
        duration=1.0,
        task_type="debug_test",
        success=True
    )
    print("✅ Direct API call recorded successfully")
    
except Exception as e:
    print(f"❌ Direct monitoring error: {e}")

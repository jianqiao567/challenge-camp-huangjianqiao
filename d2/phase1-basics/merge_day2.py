import json
import os
import logging
from datetime import datetime

script_dir = os.path.dirname(os.path.abspath(__file__))
d2_dir = os.path.normpath(os.path.join(script_dir, os.pardir, os.pardir, os.pardir, "raw", "d2"))
output_path = os.path.join(d2_dir, "merged.jsonl")
log_path = os.path.join(d2_dir, "clean.log")

logger = logging.getLogger('data_merge')
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_handler = logging.FileHandler(log_path, encoding='utf-8', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)

seen = set()
records = []
valid_count = 0
invalid_count = 0
duplicate_count = 0
error_details = []

def validate_tool_result(item, record_index):
    if not isinstance(item, dict):
        msg = f"Tool record {record_index}: Expected dict, got {type(item).__name__}"
        logger.error(msg)
        error_details.append(msg)
        return False
    
    required_fields = ['trace_id', 'tool', 'status', 'output']
    missing_fields = [f for f in required_fields if f not in item]
    if missing_fields:
        msg = f"Tool record {record_index}: Missing required fields {missing_fields}"
        logger.warning(msg)
        error_details.append(msg)
        return False
    
    valid_status = ['success', 'fail']
    if item['status'] not in valid_status:
        msg = f"Tool record {record_index}: Invalid status '{item['status']}', expected one of {valid_status}"
        logger.warning(msg)
    
    if 'latency_ms' in item:
        try:
            int(item['latency_ms'])
        except (ValueError, TypeError):
            msg = f"Tool record {record_index}: Invalid latency_ms '{item['latency_ms']}', expected integer"
            logger.warning(msg)
    
    return True

def validate_user_behavior(item, record_index):
    if not isinstance(item, dict):
        msg = f"Behavior record {record_index}: Expected dict, got {type(item).__name__}"
        logger.error(msg)
        error_details.append(msg)
        return False
    
    if 'uid' not in item and 'user_id' not in item:
        msg = f"Behavior record {record_index}: Missing user identifier (uid or user_id)"
        logger.warning(msg)
        error_details.append(msg)
        return False
    
    if 'time' not in item and 'timestamp' not in item:
        msg = f"Behavior record {record_index}: Missing time field (time or timestamp)"
        logger.warning(msg)
    
    if 'action' not in item and 'type' not in item:
        msg = f"Behavior record {record_index}: Missing action/type field"
        logger.warning(msg)
    
    if 'content' not in item and 'text' not in item:
        msg = f"Behavior record {record_index}: Missing content/text field"
        logger.warning(msg)
    
    return True

def check_file_exists(filepath):
    if not os.path.exists(filepath):
        msg = f"File not found: {filepath}"
        logger.error(msg)
        error_details.append(msg)
        return False
    if not os.path.isfile(filepath):
        msg = f"Not a file: {filepath}"
        logger.error(msg)
        error_details.append(msg)
        return False
    return True

def validate_json_structure(data, expected_type, source):
    if not isinstance(data, expected_type):
        msg = f"Invalid JSON structure in {source}: expected {expected_type.__name__}, got {type(data).__name__}"
        logger.error(msg)
        error_details.append(msg)
        return False
    return True

start_time = datetime.now()
logger.info(f"========== Data Merge Process Started ==========")
logger.info(f"Script path: {os.path.abspath(__file__)}")
logger.info(f"Working directory: {d2_dir}")
logger.info(f"Start time: {start_time}")

try:
    tool_file = os.path.join(d2_dir, "tool_result.json")
    logger.info(f"Processing tool_result.json: {tool_file}")
    
    if not check_file_exists(tool_file):
        logger.error("Skipping tool_result.json due to file issues")
    else:
        try:
            with open(tool_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                if not validate_json_structure(data, dict, "tool_result.json"):
                    logger.error("Skipping tool_result.json due to invalid structure")
                elif 'results' not in data:
                    logger.error("tool_result.json missing 'results' key")
                    error_details.append("tool_result.json missing 'results' key")
                else:
                    results = data.get('results', [])
                    if not validate_json_structure(results, list, "tool_result.json['results']"):
                        logger.error("Skipping tool_result.json due to invalid results structure")
                    else:
                        logger.info(f"Loaded {len(results)} records from tool_result.json")
                        
                        for idx, item in enumerate(results, 1):
                            if validate_tool_result(item, idx):
                                key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                                if key not in seen:
                                    seen.add(key)
                                    records.append(item)
                                    valid_count += 1
                                else:
                                    duplicate_count += 1
                                    trace_id = item.get('trace_id', 'unknown')
                                    logger.info(f"Duplicate record skipped: tool_result[{idx}] trace_id={trace_id}")
                            else:
                                invalid_count += 1

        except json.JSONDecodeError as e:
            msg = f"JSON parse error in tool_result.json: {str(e)}"
            logger.error(msg)
            error_details.append(msg)
        except Exception as e:
            msg = f"Unexpected error reading tool_result.json: {type(e).__name__}: {str(e)}"
            logger.error(msg)
            error_details.append(msg)

except Exception as e:
    msg = f"Unexpected error processing tool_result.json: {type(e).__name__}: {str(e)}"
    logger.error(msg)
    error_details.append(msg)

try:
    behavior_file = os.path.join(d2_dir, "user_behavior.json")
    logger.info(f"Processing user_behavior.json: {behavior_file}")
    
    if not check_file_exists(behavior_file):
        logger.error("Skipping user_behavior.json due to file issues")
    else:
        try:
            with open(behavior_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                if not validate_json_structure(data, list, "user_behavior.json"):
                    logger.error("Skipping user_behavior.json due to invalid structure")
                else:
                    logger.info(f"Loaded {len(data)} records from user_behavior.json")
                    
                    for idx, item in enumerate(data, 1):
                        if validate_user_behavior(item, idx):
                            key = json.dumps(item, sort_keys=True, ensure_ascii=False)
                            if key not in seen:
                                seen.add(key)
                                records.append(item)
                                valid_count += 1
                            else:
                                duplicate_count += 1
                                uid = item.get('uid', item.get('user_id', 'unknown'))
                                logger.info(f"Duplicate record skipped: user_behavior[{idx}] uid={uid}")
                        else:
                            invalid_count += 1

        except json.JSONDecodeError as e:
            msg = f"JSON parse error in user_behavior.json: {str(e)}"
            logger.error(msg)
            error_details.append(msg)
        except Exception as e:
            msg = f"Unexpected error reading user_behavior.json: {type(e).__name__}: {str(e)}"
            logger.error(msg)
            error_details.append(msg)

except Exception as e:
    msg = f"Unexpected error processing user_behavior.json: {type(e).__name__}: {str(e)}"
    logger.error(msg)
    error_details.append(msg)

try:
    if records:
        logger.info(f"Writing {len(records)} unique records to {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Successfully wrote merged.jsonl")
    else:
        msg = "No valid records to write to merged.jsonl"
        logger.warning(msg)
        error_details.append(msg)

except Exception as e:
    msg = f"Error writing merged.jsonl: {type(e).__name__}: {str(e)}"
    logger.error(msg)
    error_details.append(msg)

end_time = datetime.now()
duration = (end_time - start_time).total_seconds()

logger.info(f"========== Data Merge Process Completed ==========")
logger.info(f"End time: {end_time}")
logger.info(f"Duration: {duration:.2f} seconds")
logger.info(f"Summary:")
logger.info(f"  - Valid records processed: {valid_count}")
logger.info(f"  - Invalid records skipped: {invalid_count}")
logger.info(f"  - Duplicate records skipped: {duplicate_count}")
logger.info(f"  - Unique records written: {len(records)}")

if error_details:
    logger.info(f"Error details ({len(error_details)}):")
    for i, detail in enumerate(error_details, 1):
        logger.info(f"  {i}. {detail}")

print(f"\nMerged {len(records)} unique records to {output_path}")
print(f"Clean log written to {log_path}")
if error_details:
    print(f"Note: {len(error_details)} issues detected, please check log file for details")
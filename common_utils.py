from typing import List, Dict, Any, Union
from datetime import datetime
import json
import logging
from web3 import Web3
import re
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def initialize_web3(rpc_url: str) -> Web3:
    """初始化并返回Web3实例。"""
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    logger.info(f"Web3连接已初始化: {w3.is_connected()}")
    return w3

def find_block_by_timestamp(w3: Web3, target_timestamp: float) -> int:
    """使用二分法找到最接近目标时间戳的区块。"""
    left = 1
    right = w3.eth.get_block('latest')['number']

    while left <= right:
        mid = (left + right) // 2
        block = w3.eth.get_block(mid)
        
        if block['timestamp'] == target_timestamp:
            return mid
        elif block['timestamp'] < target_timestamp:
            left = mid + 1
        else:
            right = mid - 1

    return right

def get_event_signature(event_abi: Dict) -> str:
    """从事件 ABI 生成事件签名。"""
    if not event_abi or 'name' not in event_abi or 'inputs' not in event_abi:
        logger.warning(f"无效的事件 ABI: {event_abi}")
        return None
    
    name = event_abi['name']
    input_types = ','.join([input.get('type', '') for input in event_abi['inputs']])
    return f"{name}({input_types})"

def print_contract_events(
    contract_address: str,
    abi: List[Dict[str, Any]],
    start: Union[datetime, int],
    end: Union[datetime, int],
    rpc_url: str,
    event_name: str,
    output_queue: Any,
    stop_flag: Any,
    history_type: str
) -> List[Dict[str, Any]]:
    """
    打印指定范围内合约的特定事件交易数据。
    """
    w3 = initialize_web3(rpc_url)
    output_queue.put(f"Web3连接已初始化: {w3.is_connected()}\n")
    
    contract_address = Web3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=abi)

    if history_type == "time":
        start_block = find_block_by_timestamp(w3, start.timestamp())
        end_block = find_block_by_timestamp(w3, end.timestamp())
    else:
        start_block = start
        end_block = end

    output_queue.put(f"总区块范围: {start_block} 到 {end_block}\n")

    event_abi = next((e for e in abi if e['type'] == 'event' and e['name'] == event_name), None)
    if not event_abi:
        output_queue.put(f"未找到指定的事件: {event_name}\n")
        return []

    event_signature = get_event_signature(event_abi)
    if not event_signature:
        output_queue.put(f"无法生成事件签名: {event_name}\n")
        return []

    event_signature_hash = w3.keccak(text=event_signature).hex()
    
    current_block = start_block
    event_data = []
    event_index = 1
    while current_block <= end_block and not stop_flag():
        batch_end = min(current_block + 999, end_block)
        output_queue.put(f"处理区块范围: {current_block} 到 {batch_end}\n")
        
        try:
            logs = w3.eth.get_logs({
                'fromBlock': current_block,
                'toBlock': batch_end,
                'address': contract_address,
                'topics': [event_signature_hash]
            })
            output_queue.put(f"事件 {event_name} 在区块 {current_block} 到 {batch_end} 找到 {len(logs)} 条日志\n")
            
            for log in logs:
                if stop_flag():
                    break
                try:
                    parsed_log = contract.events[event_name]().process_log(log)
                    tx_hash = log['transactionHash'].hex()
                    tx = w3.eth.get_transaction(tx_hash)
                    block = w3.eth.get_block(log['blockNumber'])
                    
                    event_info = {
                        "交易哈希": tx_hash,
                        "区块号": log['blockNumber'],
                        "时间戳": datetime.fromtimestamp(block['timestamp']),
                        "发送者": tx['from'],
                        "接收者": tx['to'],
                        "事件参数": str(parsed_log['args'])
                    }
                    event_data.append(event_info)
                    
                    output_queue.put(f"事件 #{event_index}\n")
                    output_queue.put(f"交易哈希: {tx_hash}\n")
                    output_queue.put(f"区块号: {log['blockNumber']}\n")
                    output_queue.put(f"时间戳: {event_info['时间戳']}\n")
                    output_queue.put(f"发送者: {tx['from']}\n")
                    output_queue.put(f"接收者: {tx['to']}\n")
                    output_queue.put(f"事件参数: {parsed_log['args']}\n")
                    output_queue.put("---\n")
                    
                    event_index += 1
                except Exception as e:
                    output_queue.put(f"处理日志时出错: {e}\n")
            
        except Exception as e:
            output_queue.put(f"获取日志时出错: {str(e)}\n")
            output_queue.put(f"错误的合约地址: {contract_address}\n")
        
        current_block = batch_end + 1

    output_queue.put(f"print_contract_events 完成，返回 {len(event_data)} 个事件\n")
    return event_data

def monitor_new_events(
    contract_address: str,
    abi: List[Dict[str, Any]],
    rpc_url: str,
    event_name: str,
    output_queue: Any,
    stop_flag: Any
) -> List[Dict[str, Any]]:
    """
    持续监听并打印新的合约事件。
    """
    w3 = initialize_web3(rpc_url)
    output_queue.put(f"Web3连接已初始化: {w3.is_connected()}\n")
    
    contract_address = Web3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=abi)

    event_abi = next((e for e in abi if e['type'] == 'event' and e['name'] == event_name), None)
    if not event_abi:
        output_queue.put(f"未找到指定的事件: {event_name}\n")
        return []

    event_signature = get_event_signature(event_abi)
    if not event_signature:
        output_queue.put(f"无法生成事件签名: {event_name}\n")
        return []

    event_signature_hash = Web3.to_hex(w3.keccak(text=event_signature))
    output_queue.put(f'event_signature_hash: {event_signature_hash}\n')
    
    latest_block = w3.eth.get_block('latest')
    from_block = latest_block['number']

    output_queue.put(f"开始监听新的事件，从区块 {from_block} 开始\n")

    new_events = []
    try:
        logs = w3.eth.get_logs({
            'fromBlock': from_block,
            'toBlock': 'latest',
            'address': contract_address,
            'topics': [event_signature_hash]
        })

        for log in logs:
            if stop_flag():
                break
            try:
                parsed_log = contract.events[event_name]().process_log(log)
                tx_hash = log['transactionHash'].hex()
                tx = w3.eth.get_transaction(tx_hash)
                block = w3.eth.get_block(log['blockNumber'])
                
                event_info = {
                    "交易哈希": tx_hash,
                    "区块号": log['blockNumber'],
                    "时间戳": datetime.fromtimestamp(block['timestamp']),
                    "发送者": tx['from'],
                    "接收者": tx['to'],
                    "事件参数": str(parsed_log['args'])
                }
                new_events.append(event_info)
                
                output_queue.put(f"新事件 - 交易哈希: {tx_hash}\n")
                output_queue.put(f"区块号: {log['blockNumber']}\n")
                output_queue.put(f"时间戳: {event_info['时间戳']}\n")
                output_queue.put(f"发送者: {tx['from']}\n")
                output_queue.put(f"接收者: {tx['to']}\n")
                output_queue.put(f"事件参数: {parsed_log['args']}\n")
                output_queue.put("---\n")
            except Exception as e:
                output_queue.put(f"处理新日志时出错: {e}\n")

    except Exception as e:
        output_queue.put(f"获取新日志时出错: {e}\n")

    output_queue.put(f"返回 {len(new_events)} 个新事件\n")
    return new_events

def parse_attribute_dict(args_str):
    """解析 AttributeDict 字符串，返回解析后的字典"""
    pattern = r"AttributeDict\({(.+?)}\)"
    match = re.search(pattern, args_str)
    if match:
        args_content = match.group(1)
        args_dict = {}
        for item in args_content.split(', '):
            key, value = item.split(': ')
            key = key.strip("'")
            if value.startswith("'") and value.endswith("'"):
                value = value[1:-1]  # 移除引号
            elif value.isdigit():
                value = int(value)
            elif value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            else:
                try:
                    value = float(value)
                except ValueError:
                    pass  # 保持原始字符串
            args_dict[key] = value
        return args_dict
    return {}

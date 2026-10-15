from database.session import SessionLocal
from database.models import StockLog, ActionLog
import json


def inspect_operator_info():
    with SessionLocal() as db:
        # 检查 StockLog
        stock_logs = db.query(StockLog).limit(5).all()
        print('\nStock Logs:')
        for log in stock_logs:
            print(f'Log ID: {log.id}')
            print(f'Operator Info: {repr(log.operator_info)}')
            print(f'Raw Type: {type(log.operator_info)}')
            
            # 尝试解析 operator_info
            try:
                if isinstance(log.operator_info, str):
                    parsed = json.loads(log.operator_info)
                    print(f'Parsed: {parsed}')
            except Exception as e:
                print(f'Parse Error: {e}')
            print('-' * 50)
        
        # 检查 ActionLog
        action_logs = db.query(ActionLog).limit(5).all()
        print('\nAction Logs:')
        for log in action_logs:
            print(f'Log ID: {log.id}')
            print(f'Operator Info: {repr(log.operator_info)}')
            print(f'Raw Type: {type(log.operator_info)}')
            
            # 尝试解析 operator_info
            try:
                if isinstance(log.operator_info, str):
                    parsed = json.loads(log.operator_info)
                    print(f'Parsed: {parsed}')
            except Exception as e:
                print(f'Parse Error: {e}')
            print('-' * 50)


if __name__ == '__main__':
    inspect_operator_info()
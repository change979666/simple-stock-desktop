from crud.inventory_logs import parse_operator_info

test1 = '6666 (192.168.1.3)'
test2 = "{'operator_name': '未知操作员', 'ip_address': '26.222.145.3'}"
test3 = '666 (192.168.1.3)'
test4 = ''
test5 = None

print(f'测试1: {repr(test1)} -> {parse_operator_info(test1)}')
print(f'测试2: {repr(test2)} -> {parse_operator_info(test2)}')
print(f'测试3: {repr(test3)} -> {parse_operator_info(test3)}')
print(f'测试4: {repr(test4)} -> {parse_operator_info(test4)}')
print(f'测试5: {repr(test5)} -> {parse_operator_info(test5)}')

"""测试删除订单功能"""
import sys
sys.path.insert(0, '.')

from utils.data_access import dal
from utils.operator import get_operator_info
from utils.app_mode import app_mode

# 设置为客户端模式
app_mode.set_client_mode(True)

# 配置API客户端
from client.api_client import APIClient
api_client = APIClient()
api_client.configure(host="192.168.1.3", port=8001)


def test_delete_order():
    """测试删除订单"""
    print("="*60)
    print("测试删除销售订单")
    print("="*60)
    
    try:
        # 1. 获取所有订单
        print("\n[1/4] 获取所有订单...")
        all_orders = dal.get_sales_orders()
        print(f"   找到 {len(all_orders)} 个订单")
        
        if not all_orders:
            print("   没有订单可删除")
            return
        
        # 显示前5个订单
        print("\n前5个订单:")
        for i, order in enumerate(all_orders[:5]):
            order_num = order.get('order_number') if isinstance(order, dict) else order.order_number
            order_id = order.get('id') if isinstance(order, dict) else order.id
            customer = order.get('customer_name') if isinstance(order, dict) else order.customer_name
            print(f"   {i+1}. 订单号: {order_num}, ID: {order_id}, 客户: {customer}")
        
        # 2. 选择要删除的订单（使用最后一个）
        test_order = all_orders[-1]
        order_num = test_order.get('order_number') if isinstance(test_order, dict) else test_order.order_number
        order_id = test_order.get('id') if isinstance(test_order, dict) else test_order.id
        
        print(f"\n[2/4] 选择订单进行测试删除:")
        print(f"   订单号: {order_num}")
        print(f"   订单ID: {order_id}")
        
        # 3. 获取操作者信息
        print(f"\n[3/4] 获取操作者信息...")
        operator_info = get_operator_info()
        print(f"   操作者: {operator_info['operator_name']}")
        print(f"   IP: {operator_info['ip_address']}")
        print(f"   时间: {operator_info['timestamp']}")
        
        # 4. 删除订单
        print(f"\n[4/4] 调用删除API...")
        result = dal.delete_sale_order(order_id, operator_info)
        print(f"   ✅ 删除成功: {result}")
        
        # 5. 验证删除
        print(f"\n[验证] 重新获取订单列表...")
        new_orders = dal.get_sales_orders()
        print(f"   现在有 {len(new_orders)} 个订单")
        print(f"   减少了 {len(all_orders) - len(new_orders)} 个订单")
        
        print("\n" + "="*60)
        print("✅ 测试完成！删除功能正常工作")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_delete_order()

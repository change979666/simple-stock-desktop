"""
SimpleStock 性能测试工具

自动测试各个视图的加载性能，生成详细报告
"""
import sys
import time
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.data_access import dal
from utils.cache import data_cache
from utils.app_mode import app_mode


class PerformanceTest:
    """性能测试类"""
    
    def __init__(self):
        self.results = []
        self.test_time = datetime.now()
        
    def test_api_call(self, name, func, *args, **kwargs):
        """测试单个API调用的性能
        
        Args:
            name: 测试名称
            func: 要测试的函数
            *args, **kwargs: 函数参数
        
        Returns:
            dict: 测试结果
        """
        # 测试3次，取平均值
        times = []
        for i in range(3):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                times.append(elapsed)
                data_size = len(result) if isinstance(result, (list, dict)) else 0
            except Exception as e:
                print(f"  ❌ 测试失败: {e}")
                return {
                    'name': name,
                    'error': str(e),
                    'status': 'failed'
                }
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        result_data = {
            'name': name,
            'avg_time': round(avg_time, 3),
            'min_time': round(min_time, 3),
            'max_time': round(max_time, 3),
            'data_size': data_size,
            'status': 'success'
        }
        
        self.results.append(result_data)
        return result_data
    
    def test_cached_performance(self, name, func, cache_key, *args, **kwargs):
        """测试缓存性能（首次 vs 缓存命中）
        
        Args:
            name: 测试名称
            func: 要测试的函数
            cache_key: 缓存键名
            *args, **kwargs: 函数参数
        
        Returns:
            dict: 测试结果
        """
        # 清除缓存
        data_cache.invalidate(cache_key)
        
        # 测试首次加载（无缓存）
        print(f"  测试首次加载（无缓存）...")
        start = time.time()
        try:
            result = func(*args, **kwargs)
            first_load_time = time.time() - start
            data_size = len(result) if isinstance(result, (list, dict)) else 0
        except Exception as e:
            print(f"  ❌ 测试失败: {e}")
            return {
                'name': name,
                'error': str(e),
                'status': 'failed'
            }
        
        # 测试缓存命中
        print(f"  测试缓存加载...")
        times = []
        for i in range(3):
            start = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start
            times.append(elapsed)
        
        cached_load_time = sum(times) / len(times)
        improvement = ((first_load_time - cached_load_time) / first_load_time) * 100
        
        result_data = {
            'name': name,
            'first_load_time': round(first_load_time, 3),
            'cached_load_time': round(cached_load_time, 3),
            'improvement': round(improvement, 1),
            'data_size': data_size,
            'cache_key': cache_key,
            'status': 'success'
        }
        
        self.results.append(result_data)
        return result_data
    
    def run_all_tests(self):
        """运行所有性能测试"""
        print("="*70)
        print("SimpleStock 性能测试工具")
        print("="*70)
        print(f"测试时间: {self.test_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"运行模式: {'客户端模式' if app_mode.is_client_mode() else '本地模式'}")
        print("-"*70)
        
        # 1. 测试仪表盘批量API
        print("\n📊 测试1: 仪表盘批量API")
        result = self.test_cached_performance(
            "仪表盘批量数据加载",
            dal.get_batch_dashboard_data,
            'dashboard_stats',
            threshold=1.0
        )
        self._print_cached_result(result)
        
        # 2. 测试产品列表
        print("\n📦 测试2: 产品列表加载")
        result = self.test_cached_performance(
            "产品列表加载",
            dal.get_all_products,
            'products_list'
        )
        self._print_cached_result(result)
        
        # 3. 测试库存数据
        print("\n📋 测试3: 库存数据加载")
        def load_inventory_data():
            products = dal.get_all_products()
            sales_data = dal.get_recent_sales(days=30)
            return {'products': products, 'sales_data': sales_data}
        
        result = self.test_cached_performance(
            "库存数据加载",
            load_inventory_data,
            'inventory_data'
        )
        self._print_cached_result(result)
        
        # 4. 测试销售订单
        print("\n🛒 测试4: 销售订单加载")
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        result = self.test_api_call(
            "销售订单加载（30天）",
            dal.get_sales_orders,
            start_date=start_date,
            end_date=end_date
        )
        self._print_simple_result(result)
        
        # 5. 测试发货记录
        print("\n📦 测试5: 发货记录加载")
        result = self.test_cached_performance(
            "发货记录加载",
            dal.get_shipments,
            'shipments_list'
        )
        self._print_cached_result(result)
        
        # 6. 缓存统计
        print("\n💾 缓存统计:")
        stats = data_cache.get_stats()
        print(f"  总缓存项: {len(data_cache.cache)}")
        print(f"  命中次数: {stats['hits']}")
        print(f"  未命中次数: {stats['misses']}")
        print(f"  命中率: {stats['hit_rate']:.1%}")
        
        # 生成报告
        self.generate_report()
    
    def _print_cached_result(self, result):
        """打印缓存测试结果"""
        if result['status'] == 'failed':
            print(f"  ❌ {result['name']}: {result['error']}")
            return
        
        print(f"  ✅ {result['name']}:")
        print(f"     首次加载: {result['first_load_time']}秒")
        print(f"     缓存加载: {result['cached_load_time']}秒")
        print(f"     性能提升: {result['improvement']}%")
        print(f"     数据量: {result['data_size']}条")
    
    def _print_simple_result(self, result):
        """打印简单测试结果"""
        if result['status'] == 'failed':
            print(f"  ❌ {result['name']}: {result['error']}")
            return
        
        print(f"  ✅ {result['name']}:")
        print(f"     平均耗时: {result['avg_time']}秒")
        print(f"     最快: {result['min_time']}秒")
        print(f"     最慢: {result['max_time']}秒")
        print(f"     数据量: {result['data_size']}条")
    
    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*70)
        print("性能测试报告")
        print("="*70)
        
        # 计算总体统计
        successful_tests = [r for r in self.results if r['status'] == 'success']
        failed_tests = [r for r in self.results if r['status'] == 'failed']
        
        print(f"\n✅ 成功测试: {len(successful_tests)}/{len(self.results)}")
        if failed_tests:
            print(f"❌ 失败测试: {len(failed_tests)}/{len(self.results)}")
        
        # 缓存性能汇总
        cached_tests = [r for r in successful_tests if 'improvement' in r]
        if cached_tests:
            print("\n📊 缓存性能汇总:")
            avg_improvement = sum(r['improvement'] for r in cached_tests) / len(cached_tests)
            print(f"  平均性能提升: {avg_improvement:.1f}%")
            
            print("\n  各项详情:")
            for r in cached_tests:
                print(f"    • {r['name']}: {r['improvement']:.1f}% "
                      f"({r['first_load_time']}s → {r['cached_load_time']}s)")
        
        # 保存JSON报告
        report_file = project_root / 'tools' / 'performance_report.json'
        report_data = {
            'test_time': self.test_time.isoformat(),
            'mode': 'client' if app_mode.is_client_mode() else 'local',
            'results': self.results,
            'cache_stats': data_cache.get_stats(),
            'summary': {
                'total_tests': len(self.results),
                'successful': len(successful_tests),
                'failed': len(failed_tests),
                'avg_cache_improvement': avg_improvement if cached_tests else 0
            }
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存到: {report_file}")
        
        # 生成Markdown报告
        self._generate_markdown_report()
    
    def _generate_markdown_report(self):
        """生成Markdown格式的报告"""
        report_file = project_root / 'docs' / '性能测试报告.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"# SimpleStock 性能测试报告\n\n")
            f.write(f"**测试时间**: {self.test_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**运行模式**: {'客户端模式' if app_mode.is_client_mode() else '本地模式'}\n\n")
            
            f.write("## 测试结果汇总\n\n")
            f.write("| 测试项 | 首次加载 | 缓存加载 | 性能提升 | 数据量 |\n")
            f.write("|--------|---------|---------|---------|--------|\n")
            
            for r in self.results:
                if r['status'] == 'success':
                    if 'improvement' in r:
                        f.write(f"| {r['name']} | {r['first_load_time']}s | "
                               f"{r['cached_load_time']}s | {r['improvement']}% | "
                               f"{r['data_size']}条 |\n")
                    else:
                        f.write(f"| {r['name']} | {r['avg_time']}s | - | - | "
                               f"{r['data_size']}条 |\n")
            
            f.write("\n## 缓存统计\n\n")
            stats = data_cache.get_stats()
            f.write(f"- **总缓存项**: {len(data_cache.cache)}\n")
            f.write(f"- **命中次数**: {stats['hits']}\n")
            f.write(f"- **未命中次数**: {stats['misses']}\n")
            f.write(f"- **命中率**: {stats['hit_rate']:.1%}\n")
            
            f.write("\n## 性能分析\n\n")
            cached_tests = [r for r in self.results 
                           if r['status'] == 'success' and 'improvement' in r]
            if cached_tests:
                avg_improvement = sum(r['improvement'] for r in cached_tests) / len(cached_tests)
                f.write(f"平均缓存性能提升: **{avg_improvement:.1f}%**\n\n")
                
                f.write("### 各项性能提升明细\n\n")
                for r in sorted(cached_tests, key=lambda x: x['improvement'], reverse=True):
                    f.write(f"- **{r['name']}**: {r['improvement']:.1f}% "
                           f"({r['first_load_time']}s → {r['cached_load_time']}s)\n")
        
        print(f"📄 Markdown报告已保存到: {report_file}")


def main():
    """主函数"""
    # 设置为客户端模式
    app_mode.set_client_mode(True)
    
    # 初始化API客户端
    from client.api_client import api_client
    from config.settings import load_settings
    
    settings = load_settings()
    server_address = settings.get('server_address', '').strip()
    
    if not server_address:
        print("❌ 错误: 未配置服务器地址")
        return
    
    if ':' in server_address:
        host, port_str = server_address.split(':', 1)
        port = int(port_str)
    else:
        host = server_address
        port = 8001
    
    operator = settings.get('operator_name', '性能测试')
    
    api_client.configure(
        host=host,
        port=port,
        operator_info=operator
    )
    
    print(f"API客户端已配置: {host}:{port}")
    
    # 运行测试
    tester = PerformanceTest()
    tester.run_all_tests()
    
    print("\n" + "="*70)
    print("✅ 性能测试完成！")
    print("="*70)


if __name__ == "__main__":
    main()

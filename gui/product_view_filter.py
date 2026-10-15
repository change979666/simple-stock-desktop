    def filter_products(self):
        """根据搜索框内容过滤产品列表"""
        search_text = self.search_input.text().lower()
        
        def filter_item(item: QTreeWidgetItem):
            if not item.parent():  # 父项（产品）
                # 检查产品名称和父SKU
                parent_text = item.text(0).lower()
                if search_text in parent_text:
                    item.setHidden(False)
                    for i in range(item.childCount()):
                        item.child(i).setHidden(False)
                    return
                
                # 检查子项
                show_parent = False
                for i in range(item.childCount()):
                    child = item.child(i)
                    child_text = child.text(0).lower()
                    if search_text in child_text:
                        child.setHidden(False)
                        show_parent = True
                    else:
                        child.setHidden(True)
                item.setHidden(not show_parent)
        
        for i in range(self.product_tree.topLevelItemCount()):
            filter_item(self.product_tree.topLevelItem(i))
    def batch_edit_variants(self):
        """批量编辑子SKU"""
        selected_items = self.product_tree.selectedItems()
        variant_ids = []
        
        # 收集选中的子SKU ID
        for item in selected_items:
            if item.parent():  # 只处理子SKU
                variant_id = item.data(0, Qt.ItemDataRole.UserRole)
                if variant_id:
                    variant_ids.append(variant_id)
        
        if not variant_ids:
            QMessageBox.information(self, '提示', '请先选择要修改的子SKU！')
            return
        
        # 创建批量编辑对话框
        dialog = QDialog(self)
        dialog.setWindowTitle('批量修改')
        dialog.setFixedWidth(400)
        layout = QVBoxLayout(dialog)
        
        # 提示信息
        layout.addWidget(QLabel(f'选中了 {len(variant_ids)} 个子SKU'))
        
        # 成本价调整
        price_group = QFrame()
        price_group.setFrameStyle(QFrame.Shape.StyledPanel)
        price_layout = QVBoxLayout(price_group)
        
        # 成本价选项
        price_label = QLabel('成本价调整:')
        price_edit = QDoubleSpinBox()
        price_edit.setMinimum(0.01)
        price_edit.setMaximum(999999.99)
        price_edit.setPrefix('¥')
        
        price_layout.addWidget(price_label)
        price_layout.addWidget(price_edit)
        
        layout.addWidget(price_group)
        
        # 按钮
        btn_layout = QHBoxLayout()
        save_btn = QPushButton('保存')
        save_btn.setProperty("primary", True)
        cancel_btn = QPushButton('取消')
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 绑定按钮事件
        def save_changes():
            # ✅ 使用统一的数据访问层
            from utils.data_access import dal
            
            new_price = price_edit.value()
            operator_info = get_operator_info()
            
            # 准备批量更新数据
            variant_updates = []
            for variant_id in variant_ids:
                variant_updates.append({
                    'variant_id': variant_id,
                    'cost_price': new_price
                })
            
            try:
                # 通过API批量更新（自动处理客户端/本地模式）
                dal.batch_update_variants(variant_updates, operator_info)
                
                QMessageBox.information(
                    dialog,
                    '修改成功',
                    f'已更新 {len(variant_ids)} 个子SKU的成本价。'
                )
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(
                    dialog,
                    '修改失败',
                    f'批量修改成本价时发生错误:\n{str(e)}'
                )
        
        save_btn.clicked.connect(save_changes)
        cancel_btn.clicked.connect(dialog.reject)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_products()
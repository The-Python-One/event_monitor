# 合约事件监听器

这是一个用于监听和记录以太坊智能合约事件的图形用户界面（GUI）应用程序。它允许用户监听特定合约的历史事件或实时事件。

## 功能

- 监听指定合约地址的特定事件
- 支持历史模式（按时间范围或区块范围）和实时监听模式
- 可视化界面，易于操作
- 将监听到的事件保存为 CSV 文件
- 支持自定义 ABI 输入（文件或手动输入）
- 提供测试数据填充功能

## 安装

1. 克隆此仓库：
   ```
   git clone https://github.com/your-username/contract-event-monitor.git
   ```

2. 进入项目目录：
   ```
   cd contract-event-monitor
   ```

3. 安装所需的依赖：
   ```
   pip install -r requirements.txt
   ```

## 使用方法

1. 运行主程序：
   ```
   python event_monitor_gui.py
   ```

2. 在 GUI 中填写以下信息：
   - 合约地址
   - ABI（选择文件或手动输入）
   - 事件名称
   - RPC URL
   - 选择模式（历史或实时）
   - 如果选择历史模式，还需要填写时间范围或区块范围

3. 点击"开始监听"按钮开始监听事件

4. 监听完成后，可以点击"保存到CSV"按钮将结果保存为 CSV 文件

## 文件说明

- `event_monitor_gui.py`: 主程序，包含 GUI 代码
- `common_utils.py`: 包含共用的工具函数
- `contract_abi.json`: 默认的 ABI 文件（用于测试）

## 注意事项

- 请确保提供有效的 RPC URL 以连接到以太坊网络
- 大范围的历史查询可能需要较长时间，请耐心等待
- 实时监听模式会持续运行直到手动停止

## 贡献

欢迎提交问题和拉取请求。对于重大更改，请先开issue讨论您想要更改的内容。

## 许可证

[MIT](https://choosealicense.com/licenses/mit/)

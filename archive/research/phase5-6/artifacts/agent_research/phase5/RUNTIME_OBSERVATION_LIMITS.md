# 冻结提示中的运行环境观察

第95回会话作者使用默认CPython3.14.6准备提示，协调者用仓库支持的CPython3.12.13验证时，完整提示摘要不同。实际逐路径差异只在来源重建报告的两类叶子：

- `sources[].verification.verification_report.rebuild.current_toolchain.extractor.python`
- `sources[].verification.verification_report.rebuild.toolchain_diff.extractor.current.python`

来源记录、载体、摘录、定位、重建内容／状态及全部文件绑定一致。这些是重建时环境观察，不是文学事实或模型身份。

处理原则：先核对保存的system/messages与task/template及原prompt/request摘要完全一致，再对当前语义再渲染仅允许以上明确路径的合法CPython版本字符串变化；其他来源事实、代码版本、库版本、状态、绑定、参数、提示正文变化继续拒绝。输入字节不改，独立报告明确显示保存／当前观察差异，不伪装同一运行环境。

本说明不授予跨版本文学／来源资格，更不证明模型完整看过提示。默认3.14与支持3.12依然分别记录；provider模型、token和费用仍未验证。旧数据、旧完整提示和来源资产不因这项兼容被改写。

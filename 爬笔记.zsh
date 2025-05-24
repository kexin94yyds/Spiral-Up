#!/bin/bash

# Mac Books 高亮提取和导入脚本
# 一键提取 Books 高亮并可选择导入到备忘录

echo "📚 Mac Books 高亮提取器"
echo "======================="
echo ""

# 检查 Python 是否可用
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请安装 Python 3: https://python.org"
    exit 1
fi

# 显示菜单
echo "请选择操作:"
echo "1. 列出所有书籍"
echo "2. 导出高亮为 Markdown 格式"
echo "3. 导出高亮为 CSV 格式"
echo "4. 导出两种格式"
echo "5. 导出并自动导入到备忘录"
echo "0. 退出"
echo ""

read -p "请输入选择 (0-5): " choice

case $choice in
    1)
        echo "📖 正在列出所有书籍..."
        python3 books_highlights_extractor.py --list
        ;;
    2)
        read -p "请输入输出文件夹名称 (默认: Books_Highlights): " folder_name
        folder_name=${folder_name:-Books_Highlights}
        echo "📝 正在导出为 Markdown 格式到 $folder_name..."
        python3 books_highlights_extractor.py --export-md "$folder_name"
        ;;
    3)
        read -p "请输入 CSV 文件名 (默认: books_highlights.csv): " csv_name
        csv_name=${csv_name:-books_highlights.csv}
        echo "📊 正在导出为 CSV 格式..."
        python3 books_highlights_extractor.py --format csv --export-csv "$csv_name"
        ;;
    4)
        read -p "请输入 Markdown 文件夹名称 (默认: Books_Highlights): " folder_name
        folder_name=${folder_name:-Books_Highlights}
        read -p "请输入 CSV 文件名 (默认: books_highlights.csv): " csv_name
        csv_name=${csv_name:-books_highlights.csv}
        echo "📝📊 正在导出两种格式..."
        python3 books_highlights_extractor.py --format both --export-md "$folder_name" --export-csv "$csv_name"
        ;;
    5)
        echo "📝 正在导出 Markdown 格式..."
        python3 books_highlights_extractor.py --export-md "Books_Highlights"
        
        if [ $? -eq 0 ]; then
            echo "✅ 导出完成"
            echo "🍎 正在导入到备忘录..."
            
            # 检查 AppleScript 文件是否存在
            if [ -f "import_to_notes.applescript" ]; then
                osascript import_to_notes.applescript
            else
                echo "⚠️  找不到 import_to_notes.applescript 文件"
                echo "手动导入说明:"
                echo "1. 打开 Books_Highlights 文件夹"
                echo "2. 复制任意 .md 文件的内容"
                echo "3. 在备忘录中新建笔记并粘贴"
                open "Books_Highlights"
            fi
        else
            echo "❌ 导出失败"
        fi
        ;;
    0)
        echo "👋 再见!"
        exit 0
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "✅ 操作完成!"

# 询问是否打开输出文件夹
if [ -d "Books_Highlights" ]; then
    read -p "是否要打开输出文件夹? (y/n): " open_folder
    if [[ $open_folder =~ ^[Yy]$ ]]; then
        open "Books_Highlights"
    fi
fi 

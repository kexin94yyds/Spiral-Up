#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mac Books 高亮摘录提取器
提取 Mac Books 应用中的高亮笔记和摘录，包括颜色信息
支持导出到 Markdown 格式，便于导入备忘录
"""

import sqlite3
import os
import json
import csv
from datetime import datetime
from pathlib import Path
import argparse
import sys

class BooksHighlightExtractor:
    def __init__(self):
        # Books 数据库路径
        self.books_db_path = os.path.expanduser(
            "~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary-1-091020131601.sqlite"
        )
        
        # 注释数据库路径
        self.annotations_db_path = os.path.expanduser(
            "~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation_v10312011_1609_local.sqlite"
        )
        
        # 颜色映射
        self.color_mapping = {
            0: "黄色",  # Yellow
            1: "绿色",  # Green
            2: "蓝色",  # Blue
            3: "粉色",  # Pink
            4: "紫色",  # Purple
            5: "灰色",  # Gray
        }
        
        # Markdown 颜色样式
        self.color_styles = {
            0: "🟡",  # Yellow
            1: "🟢",  # Green
            2: "🔵",  # Blue
            3: "🩷",  # Pink
            4: "🟣",  # Purple
            5: "⚫",  # Gray
        }

    def find_books_database(self):
        """查找 Books 数据库文件"""
        possible_paths = [
            "~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/",
            "~/Library/Containers/com.apple.BKAgentService/Data/Documents/iBooks/",
        ]
        
        for path in possible_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                # 查找 SQLite 文件
                for file in os.listdir(expanded_path):
                    if file.endswith('.sqlite') and 'BKLibrary' in file:
                        self.books_db_path = os.path.join(expanded_path, file)
                        print(f"找到 Books 数据库: {self.books_db_path}")
                        return True
        return False

    def find_annotations_database(self):
        """查找注释数据库文件"""
        possible_paths = [
            "~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/",
        ]
        
        for path in possible_paths:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                # 查找 SQLite 文件
                for file in os.listdir(expanded_path):
                    if file.endswith('.sqlite') and 'AEAnnotation' in file:
                        self.annotations_db_path = os.path.join(expanded_path, file)
                        print(f"找到注释数据库: {self.annotations_db_path}")
                        return True
        return False

    def get_books_info(self):
        """获取所有书籍信息"""
        if not os.path.exists(self.books_db_path):
            if not self.find_books_database():
                print(f"错误: 找不到 Books 数据库文件")
                return []

        try:
            conn = sqlite3.connect(self.books_db_path)
            cursor = conn.cursor()
            
            # 先检查表结构
            cursor.execute("PRAGMA table_info(ZBKLIBRARYASSET)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 构建动态查询，只选择存在的列
            base_columns = ['ZASSETID', 'ZTITLE', 'ZAUTHOR']
            optional_columns = ['ZGENRE', 'ZPUBLISHER', 'ZPUBLISHDATE', 'ZLASTOPENDATE']
            
            select_columns = base_columns.copy()
            for col in optional_columns:
                if col in columns:
                    select_columns.append(col)
            
            query = f"""
            SELECT {', '.join(select_columns)}
            FROM ZBKLIBRARYASSET 
            WHERE ZTITLE IS NOT NULL
            ORDER BY {"ZLASTOPENDATE" if "ZLASTOPENDATE" in columns else "ZASSETID"} DESC
            """
            
            cursor.execute(query)
            books = cursor.fetchall()
            conn.close()
            
            return books
            
        except sqlite3.Error as e:
            print(f"数据库错误: {e}")
            return []

    def get_annotations(self, asset_id=None):
        """获取注释信息"""
        if not os.path.exists(self.annotations_db_path):
            if not self.find_annotations_database():
                print(f"错误: 找不到注释数据库文件")
                return []

        try:
            conn = sqlite3.connect(self.annotations_db_path)
            cursor = conn.cursor()
            
            # 先检查注释表结构
            cursor.execute("PRAGMA table_info(ZAEANNOTATION)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # 构建动态查询，只选择存在的列
            base_columns = ['ZANNOTATIONASSETID', 'ZANNOTATIONSELECTEDTEXT', 'ZANNOTATIONNOTE']
            optional_columns = [
                'ZANNOTATIONSTYLE', 'ZANNOTATIONCOLOR', 'ZANNOTATIONCREATIONDATE',
                'ZANNOTATIONMODIFICATIONDATE', 'ZFUTUREPROOFING5', 'ZANNOTATIONLOCATION',
                'ZANNOTATIONREPRESENTATIVETEXT'
            ]
            
            select_columns = base_columns.copy()
            for col in optional_columns:
                if col in columns:
                    select_columns.append(col)
                else:
                    # 为不存在的列添加 NULL 占位符
                    select_columns.append('NULL as ' + col)
            
            # 查询注释信息
            if asset_id:
                query = f"""
                SELECT {', '.join(select_columns)}
                FROM ZAEANNOTATION 
                WHERE ZANNOTATIONASSETID = ?
                AND (ZANNOTATIONDELETED = 0 OR ZANNOTATIONDELETED IS NULL)
                ORDER BY {"ZANNOTATIONCREATIONDATE" if "ZANNOTATIONCREATIONDATE" in columns else "rowid"} ASC
                """
                cursor.execute(query, (asset_id,))
            else:
                query = f"""
                SELECT {', '.join(select_columns)}
                FROM ZAEANNOTATION 
                WHERE (ZANNOTATIONDELETED = 0 OR ZANNOTATIONDELETED IS NULL)
                ORDER BY {"ZANNOTATIONCREATIONDATE" if "ZANNOTATIONCREATIONDATE" in columns else "rowid"} ASC
                """
                cursor.execute(query)
            
            annotations = cursor.fetchall()
            conn.close()
            
            return annotations
            
        except sqlite3.Error as e:
            print(f"注释数据库错误: {e}")
            return []

    def format_timestamp(self, timestamp):
        """格式化时间戳"""
        if timestamp is None:
            return "未知时间"
        
        # Core Data 时间戳转换 (从 2001-01-01 开始计算的秒数)
        reference_date = datetime(2001, 1, 1)
        date = reference_date.fromtimestamp(reference_date.timestamp() + timestamp)
        return date.strftime("%Y-%m-%d %H:%M:%S")

    def export_to_markdown(self, output_dir="Books_Highlights"):
        """导出高亮到 Markdown 文件"""
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print("正在获取书籍信息...")
        books = self.get_books_info()
        
        if not books:
            print("没有找到任何书籍")
            return
        
        print(f"找到 {len(books)} 本书籍")
        
        total_annotations = 0
        
        for book in books:
            # 动态解析书籍信息（适应不同的列数）
            asset_id = book[0] if len(book) > 0 else None
            title = book[1] if len(book) > 1 else "未知书名"
            author = book[2] if len(book) > 2 else None
            genre = book[3] if len(book) > 3 else None
            publisher = book[4] if len(book) > 4 else None
            publish_date = book[5] if len(book) > 5 else None
            last_open_date = book[6] if len(book) > 6 else None
            
            print(f"\n处理书籍: {title}")
            
            # 获取该书的注释
            annotations = self.get_annotations(asset_id)
            
            if not annotations:
                print(f"  - 没有找到高亮或笔记")
                continue
            
            print(f"  - 找到 {len(annotations)} 个高亮/笔记")
            total_annotations += len(annotations)
            
            # 创建 Markdown 文件
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            filename = f"{safe_title}.md"
            filepath = output_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入书籍信息
                f.write(f"# {title}\n\n")
                if author:
                    f.write(f"**作者:** {author}\n\n")
                if publisher:
                    f.write(f"**出版社:** {publisher}\n\n")
                if last_open_date:
                    f.write(f"**最后阅读:** {self.format_timestamp(last_open_date)}\n\n")
                
                f.write("---\n\n")
                f.write("## 高亮和笔记\n\n")
                
                # 写入注释
                for annotation in annotations:
                    (ann_asset_id, selected_text, note, style, color, 
                     creation_date, modification_date, future_proofing, 
                     location, representative_text) = annotation
                    
                    # 获取颜色信息
                    color_emoji = self.color_styles.get(color, "⚪")
                    color_name = self.color_mapping.get(color, "未知颜色")
                    
                    # 写入高亮文本
                    if selected_text:
                        f.write(f"### {color_emoji} 高亮 ({color_name})\n\n")
                        f.write(f"> {selected_text.strip()}\n\n")
                    
                    # 写入笔记
                    if note:
                        f.write(f"**📝 笔记:**\n\n")
                        f.write(f"{note.strip()}\n\n")
                    
                    # 写入时间信息
                    if creation_date:
                        f.write(f"*创建时间: {self.format_timestamp(creation_date)}*\n\n")
                    
                    f.write("---\n\n")
        
        print(f"\n✅ 导出完成!")
        print(f"📚 共处理 {len(books)} 本书籍")
        print(f"📝 共提取 {total_annotations} 个高亮/笔记")
        print(f"📁 文件保存在: {output_path.absolute()}")

    def export_to_csv(self, output_file="books_highlights.csv"):
        """导出到 CSV 文件"""
        
        print("正在获取书籍信息...")
        books = self.get_books_info()
        
        if not books:
            print("没有找到任何书籍")
            return
        
        # 创建书籍ID到标题的映射
        book_mapping = {}
        for book in books:
            asset_id = book[0] if len(book) > 0 else None
            title = book[1] if len(book) > 1 else "未知书名"
            author = book[2] if len(book) > 2 else "未知作者"
            book_mapping[asset_id] = {"title": title, "author": author}
        
        print("正在获取注释信息...")
        all_annotations = self.get_annotations()
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['书名', '作者', '高亮文本', '笔记', '颜色', '创建时间', '修改时间']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            
            for annotation in all_annotations:
                (asset_id, selected_text, note, style, color, 
                 creation_date, modification_date, future_proofing, 
                 location, representative_text) = annotation
                
                book_info = book_mapping.get(asset_id, {"title": "未知书籍", "author": "未知作者"})
                
                writer.writerow({
                    '书名': book_info['title'],
                    '作者': book_info['author'],
                    '高亮文本': selected_text or '',
                    '笔记': note or '',
                    '颜色': self.color_mapping.get(color, '未知颜色'),
                    '创建时间': self.format_timestamp(creation_date),
                    '修改时间': self.format_timestamp(modification_date)
                })
        
        print(f"✅ CSV 文件已保存: {output_file}")

    def list_books(self):
        """列出所有书籍"""
        books = self.get_books_info()
        
        if not books:
            print("没有找到任何书籍")
            return
        
        print(f"\n📚 找到 {len(books)} 本书籍:\n")
        
        for i, book in enumerate(books, 1):
            # 动态解析书籍信息
            asset_id = book[0] if len(book) > 0 else None
            title = book[1] if len(book) > 1 else "未知书名"
            author = book[2] if len(book) > 2 else None
            genre = book[3] if len(book) > 3 else None
            publisher = book[4] if len(book) > 4 else None
            publish_date = book[5] if len(book) > 5 else None
            last_open_date = book[6] if len(book) > 6 else None
            
            print(f"{i}. {title}")
            if author:
                print(f"   作者: {author}")
            if last_open_date:
                print(f"   最后阅读: {self.format_timestamp(last_open_date)}")
            
            # 获取该书的注释数量
            annotations = self.get_annotations(asset_id)
            print(f"   高亮/笔记数量: {len(annotations)}")
            print()

def main():
    parser = argparse.ArgumentParser(description='Mac Books 高亮摘录提取器')
    parser.add_argument('--list', action='store_true', help='列出所有书籍')
    parser.add_argument('--export-md', metavar='DIR', default='Books_Highlights', 
                       help='导出到 Markdown 文件夹 (默认: Books_Highlights)')
    parser.add_argument('--export-csv', metavar='FILE', default='books_highlights.csv',
                       help='导出到 CSV 文件 (默认: books_highlights.csv)')
    parser.add_argument('--format', choices=['markdown', 'csv', 'both'], default='markdown',
                       help='导出格式 (默认: markdown)')
    
    args = parser.parse_args()
    
    extractor = BooksHighlightExtractor()
    
    if args.list:
        extractor.list_books()
    elif args.format == 'markdown':
        extractor.export_to_markdown(args.export_md)
    elif args.format == 'csv':
        extractor.export_to_csv(args.export_csv)
    elif args.format == 'both':
        extractor.export_to_markdown(args.export_md)
        extractor.export_to_csv(args.export_csv)

if __name__ == "__main__":
    main() 

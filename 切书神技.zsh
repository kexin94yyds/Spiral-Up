#!/bin/zsh

# Path to pandoc
PANDOC_CMD="/opt/homebrew/bin/pandoc"

# Get the selected EPUB file
EPUB_FILE="$1"

# Define paths
ZIP_FILE="${EPUB_FILE%.epub}.zip"
TMP_DIR=$(mktemp -d)
OUTPUT_DIR="${EPUB_FILE%.epub}"
MD_DIR="$OUTPUT_DIR/markdown"
TXT_DIR="$OUTPUT_DIR/txt"

# Create output directories
mkdir -p "$OUTPUT_DIR/html"
mkdir -p "$MD_DIR"
mkdir -p "$TXT_DIR"

# Copy and rename the EPUB to a ZIP file
cp "$EPUB_FILE" "$ZIP_FILE"

# Unzip the file
unzip -q "$ZIP_FILE" -d "$TMP_DIR"

# Locate the OEBPS folder and handle different EPUB structures
OEBPS_DIR=$(find "$TMP_DIR" -type d -name "OEBPS" -o -name "OPS" -o -name "content")
if [ -z "$OEBPS_DIR" ]; then
    OEBPS_DIR="$TMP_DIR"
fi

# Copy HTML content
cp -R "$OEBPS_DIR"/* "$OUTPUT_DIR/html/"

# Function to clean markdown content
clean_markdown() {
    local file="$1"
    sed -i '' -e 's/<[^>]*>//g' "$file"
    sed -i '' -e '/^[[:space:]]*$/d' "$file"
    sed -i '' -e 's/^[[:space:]]*//;s/[[:space:]]*$//' "$file"
}

# Function to clean filename
clean_filename() {
    local title="$1"
    # Remove HTML tags first
    title=$(echo "$title" | sed 's/<[^>]*>//g')
    # Remove leading/trailing whitespace
    title=$(echo "$title" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    # Replace problematic characters
    title=$(echo "$title" | sed 's/[\/\*\?:<>"|]/_/g')
    # Remove multiple consecutive spaces and replace with underscore
    title=$(echo "$title" | sed 's/[[:space:]]\+/_/g')
    # Limit length to avoid filesystem issues
    if [ ${#title} -gt 100 ]; then
        title="${title:0:100}"
    fi
    # If title is empty or only contains punctuation, use a default
    if [[ -z "$title" || "$title" =~ ^[[:punct:]_]+$ ]]; then
        title="untitled"
    fi
    echo "$title"
}

# Function to extract chapter title from content
extract_chapter_title() {
    local file="$1"
    local index="$2"
    
    local title=""
    
    # Convert to plain text first to extract potential title
    local temp_txt=$(mktemp)
    "$PANDOC_CMD" "$file" -f html -t plain --wrap=none -o "$temp_txt" 2>/dev/null
    
    # First try to extract from the first few lines of content
    # Look for common chapter patterns in the first few lines
    title=$(head -10 "$temp_txt" | grep -E '^[0-9]+\s+.*|^第[一二三四五六七八九十百千万甲乙丙丁戊己庚辛壬癸]+[章节回].*|^Chapter\s+.*|^目录|^序言|^前言|^后记|^附录' | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    
    # If no clear pattern found, try the first non-empty line that looks like a title
    if [ -z "$title" ]; then
        title=$(head -5 "$temp_txt" | grep -v '^[[:space:]]*$' | head -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    fi
    
    # If still no title from content, try HTML/XHTML title tags or h1-h6 tags
    if [ -z "$title" ]; then
        # Try title tag
        title=$(grep -i '<title>' "$file" | head -1 | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # If no title, try h1-h6 tags
        if [ -z "$title" ]; then
            title=$(grep -i '<h[1-6][^>]*>' "$file" | head -1 | sed 's/<[^>]*>//g' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        fi
    fi
    
    rm -f "$temp_txt"
    
    # Clean the title for use as filename
    if [ -n "$title" ]; then
        title=$(clean_filename "$title")
    else
        title="index_split_$(printf "%03d" $index)"
    fi
    
    echo "$title"
}

# 创建文件数组
files=()
while IFS= read -r file; do
    files+=("$file")
done < <(find "$OEBPS_DIR" \( -name "*.html" -o -name "*.xhtml" \) -type f | sort)

# 处理 Markdown 转换
echo "Converting chapters to Markdown..."
index=0
for file in "${files[@]}"; do
    BASENAME=$(basename "$file" | sed "s/\.[^.]*$//")
    
    # Extract chapter title
    CHAPTER_TITLE=$(extract_chapter_title "$file" $index)
    
    OUTPUT_FILE="$MD_DIR/${CHAPTER_TITLE}.md"
    
    "$PANDOC_CMD" "$file" \
        -f html+raw_html \
        -t markdown-raw_html \
        --wrap=none \
        --extract-media="$OUTPUT_DIR/images" \
        --standalone \
        -o "$OUTPUT_FILE"
    
    clean_markdown "$OUTPUT_FILE"
    echo "✓ Converted to Markdown: $CHAPTER_TITLE"
    
    # 添加 TXT 转换
    TXT_OUTPUT="$TXT_DIR/${CHAPTER_TITLE}.txt"
    "$PANDOC_CMD" "$file" \
        -f html \
        -t plain \
        --wrap=none \
        -o "$TXT_OUTPUT"
    
    sed -i '' -e '/^[[:space:]]*$/d' "$TXT_OUTPUT"
    sed -i '' -e 's/^[[:space:]]*//;s/[[:space:]]*$//' "$TXT_OUTPUT"
    echo "✓ Converted to TXT: $CHAPTER_TITLE"
    
    ((index++))
done

# 创建完整的合并文档
echo "Creating complete files..."
# Markdown 版本
{
    echo "---"
    echo "title: \"$(basename "${EPUB_FILE%.epub}")\""
    echo "date: $(date +%Y-%m-%d)"
    echo "---"
    echo
    
    index=0
    for file in "${files[@]}"; do
        BASENAME=$(basename "$file" | sed "s/\.[^.]*$//")
        CHAPTER_TITLE=$(extract_chapter_title "$file" $index)
        chapter_file="$MD_DIR/${CHAPTER_TITLE}.md"
        if [ -f "$chapter_file" ]; then
            awk '!/^---$/{p=1;next} p&&!/^---$/' "$chapter_file"
            echo -e "\n\n---\n\n"
        fi
        ((index++))
    done
} > "$OUTPUT_DIR/complete.md"

# TXT 结构化版本
{
    echo "$(basename "${EPUB_FILE%.epub}")"
    echo "================================"
    echo
    
    index=0
    for file in "${files[@]}"; do
        BASENAME=$(basename "$file" | sed "s/\.[^.]*$//")
        CHAPTER_TITLE=$(extract_chapter_title "$file" $index)
        chapter_file="$TXT_DIR/${CHAPTER_TITLE}.txt"
        if [ -f "$chapter_file" ]; then
            echo "## ${CHAPTER_TITLE}"
            echo "--------------------------------"
            cat "$chapter_file"
            echo -e "\n\n"
        fi
        ((index++))
    done
} > "$OUTPUT_DIR/complete_structured.txt"

# 创建索引文件
{
    echo "# $(basename "${EPUB_FILE%.epub}")"
    echo "## 目录"
    echo
    index=0
    for file in "${files[@]}"; do
        BASENAME=$(basename "$file" | sed "s/\.[^.]*$//")
        CHAPTER_TITLE=$(extract_chapter_title "$file" $index)
        echo "- [${CHAPTER_TITLE}](markdown/${CHAPTER_TITLE}.md)"
        ((index++))
    done
} > "$MD_DIR/index.md"

{
    echo "目录"
    echo "======"
    echo
    index=0
    for file in "${files[@]}"; do
        BASENAME=$(basename "$file" | sed "s/\.[^.]*$//")
        CHAPTER_TITLE=$(extract_chapter_title "$file" $index)
        echo "* ${CHAPTER_TITLE}"
        ((index++))
    done
} > "$TXT_DIR/index.txt"

# Cleanup
rm -rf "$TMP_DIR"
rm "$ZIP_FILE"

echo "Conversion completed!"
osascript -e "display notification \"Conversion completed! Output in: $OUTPUT_DIR\" with title \"EPUB Processor\""
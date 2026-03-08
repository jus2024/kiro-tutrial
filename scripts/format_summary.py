#!/usr/bin/env python3
"""
Format and display memo summary results in a readable format.
"""
import json
import sys


def print_usage():
    """Print usage information."""
    print("Usage: format_summary.py [FILE]")
    print("Format and display memo summary results.")
    print()
    print("Arguments:")
    print("  FILE    JSON file containing summary response (optional)")
    print("          If not provided, reads from stdin")
    print()
    print("Examples:")
    print("  format_summary.py response.json")
    print("  curl $API_URL/memos/summary -X POST -d '{}' | format_summary.py")


def format_summary(response_data):
    """Format the summary response for better readability.
    
    Args:
        response_data: JSON string or dictionary containing summary response
    """
    
    # Parse JSON if string
    try:
        if isinstance(response_data, str):
            response_data = json.loads(response_data)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format - {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check if this is an error response
    if 'error' in response_data:
        error = response_data['error']
        print("\n" + "="*80)
        print("❌ エラー")
        print("="*80 + "\n")
        print(f"コード: {error.get('code', 'Unknown')}")
        print(f"メッセージ: {error.get('message', 'No message')}")
        if 'request_id' in error:
            print(f"リクエストID: {error['request_id']}")
        print("\n" + "="*80 + "\n")
        return
    
    # Validate required fields
    if 'summary' not in response_data:
        print("❌ Error: Missing 'summary' field in response", file=sys.stderr)
        sys.exit(1)
    
    summary = response_data.get('summary', '')
    metadata = response_data.get('metadata', {})
    
    # Print header
    print("\n" + "="*80)
    print("📝 メモ要約結果")
    print("="*80 + "\n")
    
    # Print metadata with safe defaults
    print("📊 処理情報:")
    processing_time = metadata.get('processing_time_ms', 0)
    if processing_time > 0:
        print(f"  • 処理時間: {processing_time / 1000:.2f}秒")
    else:
        print(f"  • 処理時間: N/A")
    
    memos_included = metadata.get('memos_included', 0)
    memos_total = metadata.get('memos_total', 0)
    print(f"  • 要約対象: {memos_included}/{memos_total}件のメモ")
    print(f"  • モデル: {metadata.get('model_id', 'N/A')}")
    
    truncated = metadata.get('truncated', False)
    print(f"  • 切り詰め: {'あり' if truncated else 'なし'}")
    print("\n" + "-"*80 + "\n")
    
    # Print summary content
    print("📄 要約内容:\n")
    print(summary)
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    # Handle help flag
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print_usage()
        sys.exit(0)
    
    try:
        if len(sys.argv) > 1:
            # Read from file
            with open(sys.argv[1], 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # Read from stdin
            data = json.load(sys.stdin)
        
        format_summary(data)
    except FileNotFoundError:
        print(f"❌ Error: File '{sys.argv[1]}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON - {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

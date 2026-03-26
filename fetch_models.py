import asyncio, json
import sys
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://docs.windsurf.com/windsurf/models"  # 英語版URL（最新情報）
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_JSON = SCRIPT_DIR / "Windsurf_Self-serve_models_output.json"
OUTPUT_MD = SCRIPT_DIR / "Windsurf_Self-serve_models_table.md"

# タブとテーブルを特定するセレクタ/XPath
TAB_CONTAINER_XPATH = '/html/body/div[2]/div/div[1]/div[2]/div[2]/div/div/div[1]/div[3]'
TAB_SELECTOR = 'button, [role="tab"]'
TABLE_ROWS = 'table tbody tr, [role="table"] [role="row"]'
TABLE_CELLS = 'td, [role="cell"]'

async def main():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # タイムアウト増加 & DOM読み込み優先（ネットワーク待ちで固まらないように）
        page.set_default_timeout(90000)
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)

        # 英語版ページでは動的コンポーネントを使用しているため、
        # Self-serveタブ内のサブタブ構造（Recommended、Windsurf、Anthropicなど）に対応
        result = {}
        
        try:
            # まずSelf-serveタブを探してクリック
            main_tabs = await page.query_selector_all('[role="tab"], button[role="tab"], .tab-button')
            
            self_serve_tab = None
            for tab in main_tabs:
                tab_text = await tab.inner_text()
                if "Self-serve" in tab_text:
                    self_serve_tab = tab
                    break
            
            if self_serve_tab:
                await self_serve_tab.click()
                await page.wait_for_timeout(1500)  # サブタブ読み込み待ち
                
                # Self-serveタブ内のサブタブを探す（cost-tab-buttonクラスを優先使用）
                sub_tabs_selectors = [
                    '.cost-tab-button',
                    '[role="tab"]',
                    'button[role="tab"]',
                    '.tab-button',
                    'button[data-tab]',
                    '.tabs button'
                ]
                
                all_sub_tabs = []
                for selector in sub_tabs_selectors:
                    tabs = await page.query_selector_all(selector)
                    if tabs:
                        all_sub_tabs.extend(tabs)
                        if selector == '.cost-tab-button' and tabs:
                            print(f"cost-tab-buttonクラスで {len(tabs)} 個のサブタブを発見")
                            break  # cost-tab-buttonが見つかれば他は探さない
                
                # 重複を除去してサブタブをフィルタリング
                seen_texts = set()
                actual_sub_tabs = []
                
                for sub_tab in all_sub_tabs:
                    try:
                        sub_text = await sub_tab.inner_text()
                        sub_text = sub_text.strip()
                        
                        # メインタブと重複するものを除外
                        if (sub_text and 
                            sub_text not in seen_texts and
                            "Self-serve" not in sub_text and 
                            "Enterprise" not in sub_text and
                            len(sub_text) > 0):
                            
                            # 有効なサブタブ名かチェック
                            valid_names = ["Recommended", "Windsurf", "Anthropic", "OpenAI", "Google", "Other"]
                            if any(name in sub_text for name in valid_names) or sub_text in valid_names:
                                seen_texts.add(sub_text)
                                actual_sub_tabs.append((sub_text, sub_tab))
                    except:
                        continue
                
                if actual_sub_tabs:
                    # 各サブタブをクリックしてデータを取得
                    for sub_tab_name, sub_tab_element in actual_sub_tabs:
                        try:
                            print(f"サブタブ '{sub_tab_name}' を処理中...")
                            await sub_tab_element.click()
                            await page.wait_for_timeout(1000)  # コンテンツ読み込み待ち
                            

                            # 各タブに特化したデータ取得（価格表記でフィルタリング）
                            tab_data = []
                            
                            try:
                                # JavaScriptでデータ取得（価格表記でフィルタリング）
                                data = await page.evaluate("""
                                    () => {
                                        const results = [];
                                        const tables = document.querySelectorAll('table');
                                        
                                        tables.forEach(table => {
                                            const rows = table.querySelectorAll('tr');
                                            rows.forEach(row => {
                                                const cells = row.querySelectorAll('td, th');
                                                if (cells.length >= 4) {
                                                    const model = cells[0].textContent.trim();
                                                    const inputCost = cells[1].textContent.trim();
                                                    const cacheInputCost = cells[2].textContent.trim();
                                                    const outputCost = cells[3].textContent.trim();
                                                    
                                                    // 価格表記でフィルタリング（$または—のみ）
                                                    const hasValidCost = inputCost.startsWith('$') || inputCost === '—' || inputCost === '-';
                                                    
                                                    if (model && hasValidCost &&
                                                        !model.toLowerCase().includes('model') && 
                                                        !model.toLowerCase().includes('name') &&
                                                        model.length > 0) {
                                                        results.push({
                                                            model: model,
                                                            input_cost: inputCost,
                                                            cache_input_cost: cacheInputCost,
                                                            output_cost: outputCost
                                                        });
                                                    }
                                                }
                                            });
                                        });
                                        
                                        return results;
                                    }
                                """)
                                
                                if data:
                                    tab_data = data
                                    print(f"'{sub_tab_name}' から {len(tab_data)} モデルを取得（価格フィルタ適用）")
                                else:
                                    print(f"'{sub_tab_name}' にはモデルデータがありませんでした")
                                    
                            except Exception as js_error:
                                print(f"JavaScript実行エラー: {js_error}")
                                # フォールバック：4列対応
                                tables = await page.query_selector_all('table')
                                for table in tables[:2]:  # 最初の2テーブルのみ
                                    rows = await table.query_selector_all('tr')
                                    for row in rows:
                                        cells = await row.query_selector_all('td, th')
                                        if len(cells) >= 4:
                                            model = await cells[0].inner_text()
                                            input_cost = await cells[1].inner_text()
                                            cache_input_cost = await cells[2].inner_text()
                                            output_cost = await cells[3].inner_text()
                                            model = model.strip()
                                            input_cost = input_cost.strip()
                                            cache_input_cost = cache_input_cost.strip()
                                            output_cost = output_cost.strip()
                                            # 価格表記でフィルタリング
                                            if model and (input_cost.startswith('$') or input_cost in ['—', '-']) and \
                                               not model.lower().startswith('model') and not model.lower().startswith('name'):
                                                tab_data.append({
                                                    "model": model,
                                                    "input_cost": input_cost,
                                                    "cache_input_cost": cache_input_cost,
                                                    "output_cost": output_cost
                                                })
                            

                            if tab_data:
                                result[sub_tab_name] = tab_data
                                print(f"'{sub_tab_name}' から {len(tab_data)} モデルを取得")
                            else:
                                print(f"'{sub_tab_name}' にはモデルデータがありませんでした")
                                
                        except Exception as sub_tab_error:
                            print(f"サブタブ '{sub_tab_name}' の処理中にエラー: {sub_tab_error}")
                            continue
                else:
                    print("サブタブが見つかりませんでした。現在のテーブルを取得します...")
                    # サブタブがない場合は現在表示されているテーブルを取得
                    tables = await page.query_selector_all('table')
                    all_data = []
                    for table in tables:
                        rows = await table.query_selector_all('tr')
                        for row in rows:
                            cells = await row.query_selector_all('td, th')
                            if len(cells) >= 4:
                                model = await cells[0].inner_text()
                                input_cost = await cells[1].inner_text()
                                cache_input_cost = await cells[2].inner_text()
                                output_cost = await cells[3].inner_text()
                                model = model.strip()
                                input_cost = input_cost.strip()
                                cache_input_cost = cache_input_cost.strip()
                                output_cost = output_cost.strip()
                                if model and (input_cost.startswith('$') or input_cost in ['—', '-']) and \
                                   not model.lower().startswith('model') and not model.lower().startswith('name'):
                                    all_data.append({
                                        "model": model,
                                        "input_cost": input_cost,
                                        "cache_input_cost": cache_input_cost,
                                        "output_cost": output_cost
                                    })
                    
                    if all_data:
                        result["Self-serve"] = all_data
            else:
                print("Self-serveタブが見つかりませんでした")
                # Self-serveタブが見つからない場合は全テーブルを取得
                tables = await page.query_selector_all('table')
                all_data = []
                for table in tables:
                    rows = await table.query_selector_all('tr')
                    for row in rows:
                        cells = await row.query_selector_all('td, th')
                        if len(cells) >= 4:
                            model = await cells[0].inner_text()
                            input_cost = await cells[1].inner_text()
                            cache_input_cost = await cells[2].inner_text()
                            output_cost = await cells[3].inner_text()
                            model = model.strip()
                            input_cost = input_cost.strip()
                            cache_input_cost = cache_input_cost.strip()
                            output_cost = output_cost.strip()
                            if model and (input_cost.startswith('$') or input_cost in ['—', '-']) and \
                               not model.lower().startswith('model') and not model.lower().startswith('name'):
                                all_data.append({
                                    "model": model,
                                    "input_cost": input_cost,
                                    "cache_input_cost": cache_input_cost,
                                    "output_cost": output_cost
                                })
                
                if all_data:
                    result["All"] = all_data
            
            if not result:
                print("警告: 価格情報を取得できませんでした")
            else:
                print(f"合計 {len(result)} 個のタブからデータを取得しました")
                
        except Exception as e:
            print(f"エラー: 価格情報取得中に問題が発生しました - {e}")

        # 出力をUTF-8でファイル保存し、標準出力の文字化け・encodeエラーを回避
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

        # PermissionError対策: 既存ファイルがロック中ならタイムスタンプ付きで退避
        def safe_write(path: Path, content: str):
            if path.exists():
                try:
                    path.unlink()
                except PermissionError:
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    path.rename(path.with_stem(f"{path.stem}_{ts}"))
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

        # 取得日時
        fetch_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # JSON出力（取得日時を含む）
        json_output = {
            "_metadata": {
                "fetch_datetime": fetch_datetime,
                "source_url": URL
            },
            "data": result
        }
        safe_write(OUTPUT_JSON, json.dumps(json_output, ensure_ascii=False, indent=2))

        # Markdown生成（無料モデルを先頭、続いて有料モデル）
        def sanitize(text: str) -> str:
            return text.replace("|", "｜")
        
        def normalize_cost(cost_str: str) -> str:
            """価格表記を正規化（$記号の欠けを修正）"""
            cost = cost_str.strip()
            
            # すでに$記号があるかプロモーション文言を含む場合はそのまま
            if cost.startswith("$") or "Promo" in cost or cost in ("—", "-"):
                return cost
            
            # 数字のみの場合は$記号を追加
            if cost and cost.replace(".", "").isdigit():
                return f"${cost}"
            
            return cost
        
        def is_free_model(item: dict) -> bool:
            """無料モデルかどうか判定"""
            input_cost = item.get("input_cost", "")
            cache_cost = item.get("cache_input_cost", "")
            output_cost = item.get("output_cost", "")
            
            for cost in [input_cost, cache_cost, output_cost]:
                if cost and not (cost in ("—", "-", "$0.00", "0", "0.00") or not cost):
                    return False
            return True

        # Markdown生成（取得日時を先頭に追加）
        md_lines = []
        md_lines.append(f"# Windsurf Self-serve モデル一覧")
        md_lines.append("")
        md_lines.append(f"**取得日時**: {fetch_datetime}")
        md_lines.append("")
        md_lines.append(f"**取得元**: [{URL}]({URL})")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")
        free_models = []
        paid_models = []
        seen_models = set()  # 重複排除用
        
        for tab_items in result.values():
            for item in tab_items:
                model_name = item.get("model", "").strip()
                if not model_name or model_name in seen_models:
                    continue
                seen_models.add(model_name)
                
                # 価格表記を正規化
                item["input_cost"] = normalize_cost(item.get("input_cost", "—"))
                item["cache_input_cost"] = normalize_cost(item.get("cache_input_cost", "—"))
                item["output_cost"] = normalize_cost(item.get("output_cost", "—"))
                
                # 無料か有料か判定
                if is_free_model(item):
                    free_models.append(item)
                else:
                    paid_models.append(item)

        # 無料モデルセクション
        md_lines.append("## 無料モデル")
        md_lines.append("| モデル名 | 入力 (100万トークン) | キャッシュ入力 (100万トークン) | 出力 (100万トークン) |")
        md_lines.append("|---------|---------------------|---------------------------|---------------------|")
        for item in free_models:
            md_lines.append(f"| {sanitize(item['model'])} | {item['input_cost']} | {item['cache_input_cost']} | {item['output_cost']} |")
        md_lines.append("")

        # 有料モデルセクション
        md_lines.append("## 有料モデル (Self-serve)")
        md_lines.append("| モデル名 | 入力 (100万トークン) | キャッシュ入力 (100万トークン) | 出力 (100万トークン) |")
        md_lines.append("|---------|---------------------|---------------------------|---------------------|")
        for item in paid_models:
            md_lines.append(f"| {sanitize(item['model'])} | {item['input_cost']} | {item['cache_input_cost']} | {item['output_cost']} |")
        md_lines.append("")

        # BYOKモデル情報（固定）
        md_lines.append("## BYOK (Bring Your Own Key) モデル")
        md_lines.append("| モデル名 | 備考 |")
        md_lines.append("|---------|------|")
        byok_models = [
            "Claude 4 Sonnet",
            "Claude 4 Sonnet (Thinking)", 
            "Claude 4 Opus",
            "Claude 4 Opus (Thinking)"
        ]
        for model in byok_models:
            md_lines.append(f"| {model} | 自身のAPIキーが必要 |")

        safe_write(OUTPUT_MD, "\n".join(md_lines))

        print(f"Saved to {OUTPUT_JSON} and {OUTPUT_MD}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
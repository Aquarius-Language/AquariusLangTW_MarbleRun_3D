# 彈珠競速－高空速降

完全以 Aquarius（`.aqua`）撰寫的 3D 計時競速遊戲。操控條紋彈珠沿著蜿蜒的高架賽道向下滾動，依序通過六道檢查門，挑戰自己的最佳紀錄。金色檢查門代表下一個檢查點，已通過的檢查門會變成綠色。墜落後會在上一個檢查點重生，並加罰 3 秒。

在 24 秒內完賽可獲得金牌，38 秒內則可獲得銀牌。最佳紀錄僅保留至本次遊戲關閉。遊戲介面、操作提示與視窗標題皆使用繁體中文。

## 遊戲預覽

![彈珠競速遊戲畫面：條紋彈珠、高架賽道、金色檢查門、計時器與小地圖](preview.png)

繪圖透過 **Processing P3D 使用 wgpu**，搭配自訂 WGSL 材質、深度緩衝、方向光、鏡面高光與距離霧效。Processing 負責 GPU 畫布呈現，以及 GLFW 視窗與輸入整合。

**Jolt Physics** 負責模擬彈珠與具有旋轉角度的方塊賽道，包含重力、摩擦、滾動、護欄碰撞及連續碰撞偵測。遊戲不需要外部美術素材，也不需要修改語言執行環境。

## 網頁版與 GitHub Pages

網頁版網址：[彈珠競速－高空速降](https://aquarius-language.github.io/AquariusLangTW_MarbleRun_3D/)（首次部署成功後即可使用）。請使用支援 WebGPU 的瀏覽器。

`web/` 包含已建置的遊戲、JavaScript 模組與 WebAssembly 相依檔案，可直接作為靜態網站發佈，不需要在 GitHub Actions 中重新編譯 Aquarius 腳本。

啟用部署：

1. 在儲存庫 **Settings → Pages → Build and deployment → Source** 選擇 **GitHub Actions**。
2. 將 `.github/workflows/pages.yml` 推送至 `main`。首次推送工作流程，以及後續 `main` 上的 `web/` 或工作流程更新，都會自動部署。
3. 亦可在 **Actions → Deploy game to GitHub Pages → Run workflow** 選擇 `main` 手動部署。成功後，`github-pages` 環境會顯示網站連結。

工作流程僅發佈 `web/` 的內容。修改 `.aqua` 來源後，請先重新建置網頁版並提交更新後的 `web/` 檔案，再部署網站。

## 執行方式

請使用支援雙語函式的 **`AquariusDesktopVMREPL.exe`**（AquariusLangTW `6331675`／2026-10-08 或更新版本），保留隨附的繪圖與物理相依套件，並確認電腦具有相容的 GPU 驅動程式。遊戲介面使用系統字型 **Microsoft JhengHei（微軟正黑體）**；請使用支援繁體中文字型的 Windows 執行環境。

請將完整執行環境放在同一個目錄中。在遊戲目錄下，以執行檔啟動入口腳本：

```powershell
# 執行檔已加入 PATH 時：
AquariusDesktopVMREPL.exe .\main.aqua

# 或指定執行檔的完整路徑：
& 'C:\Aquarius\AquariusDesktopVMREPL.exe' .\main.aqua
```

請將範例路徑替換成實際的執行檔位置。腳本匯入路徑以各腳本所在目錄為基準，因此也可以指定 `main.aqua` 的絕對路徑，從其他工作目錄啟動。

## 操作方式

| 按鍵 | 功能 |
| --- | --- |
| WASD／方向鍵 | 沿世界座標的 X／Z 軸轉向：W 朝賽道下坡方向移動，D 向右移動 |
| 空白鍵（按住） | 減緩水平移動速度 |
| J | 彈珠位於賽道上時跳躍 |
| R | 回到上一個檢查點，並加罰 3 秒 |
| Enter | 重新開始，保留本次遊戲的最佳紀錄 |
| P | 暫停／繼續物理模擬與計時 |
| C | 切換跟隨／俯瞰鏡頭 |
| 滑鼠滾輪 | 調整跟隨鏡頭距離 |
| Esc／關閉視窗 | 離開遊戲 |

按 W 或上方向鍵出發並開始計時。下坡速度主要來自重力；進入沒有護欄的彎道前先煞車，並朝醒目的金色檢查門前進。俯瞰鏡頭與小地圖可查看完整路線。兩種鏡頭模式的轉向方向都以世界座標為準。鏡頭與遊戲介面會隨視窗大小及顯示器像素密度調整。

## 腳本說明

| 腳本 | 職責 |
| --- | --- |
| `main.aqua` | 模組整合、繪圖生命週期、時鐘與事件連接 |
| `config.aqua` | 賽道節點、尺寸、物理參數與獎牌目標時間 |
| `math3d.aqua` | 向量運算，以及對應的四元數與矩陣轉換 |
| `track.aqua` | 共用的地板、護欄、支柱與檢查點定義 |
| `physics.aqua` | Jolt 資源管理、固定時間更新、操控、重生與成績計算 |
| `input.aqua` | 持續按鍵輸入與斜向轉向的正規化 |
| `camera.aqua` | 平滑跟隨視角、俯瞰視角與縮放 |
| `shaders.aqua` | WGSL 頂點與片段著色器 |
| `renderer.aqua` | GPU 畫布、賽道幾何、檢查點與滾動彈珠 |
| `hud.aqua` | 計時、進度、小地圖、操作提示、暫停與結果面板 |
| `smoke.aqua` | 使用原生繪圖與物理引擎的自動整合驗證 |

專案自訂的變數、函式繫結、參數與著色器變數皆使用繁體中文名稱。Processing、畫布、著色器與 Jolt 的函式呼叫亦全部使用雙語 API 的繁體中文名稱（例如 `尺寸`、`建立畫布`、`套用矩陣`、`建立世界`、`步進`、`釋放`），名稱依據 [AquariusLangTW 雙語函式對照表](https://github.com/Aquarius-Language/AquariusLangTW/blob/6331675d9ba8571a5997690c429d1c5660148cc7/AquariusDesktopVMREPL/LIBRARY_NAMES.md)。模組名稱、常數、屬性、事件字串與 WGSL 入口及內建介面仍使用執行環境要求的原名。

修改 `config.aqua` 即可調整路線或移動參數。相鄰節點會建立具有旋轉角度的斜坡，寬大的平台則銜接各個轉角。碰撞體與繪圖幾何共用位置、尺寸及旋轉資料。拱門、棋盤格地磚與背景網格皆為裝飾。高架賽道下方的地面僅供顯示；彈珠落至回復高度以下時，就會觸發重生。

物理模擬透過時間累加器以 **120 Hz** 更新，繪圖時則使用位置插值。每個畫格的時間差上限為 0.1 秒，最多執行 12 次更新，避免長時間停頓後無限追趕進度。計時器累計模擬時間與重生罰時。煞車透過阻力減速；是否能跳躍由旋轉後的地板範圍判定，所有碰撞反應則由 Jolt 處理。抵達終點後，該次挑戰即停止更新。

正常離開時會釋放 Jolt 資源；若腳本或回呼發生錯誤，桌面執行環境也會釋放原生資源。Processing 會釋放視窗與 GPU 資源。

## 編譯成可攜式腳本瓶（bottle）

請打包**所有**腳本，並將 `main.aqua` 放在第一個。在遊戲目錄下，使用相同的預先建置執行檔：

```powershell
$彈珠執行器 = 'C:\Aquarius\AquariusDesktopVMREPL.exe'
$彈珠腳本列表 = @('.\main.aqua') + @(
    Get-ChildItem . -Filter *.aqua |
    Where-Object Name -ne 'main.aqua' |
    Sort-Object Name |
    ForEach-Object FullName
)
& $彈珠執行器 -c --root . -o .\marble_run.bottle @彈珠腳本列表
& $彈珠執行器 .\marble_run.bottle
```

腳本瓶包含 WGSL 字串，不需要美術素材檔案。發佈時，請一併提供完整的桌面 VM 與原生相依套件。

## 驗證遊戲

整合驗證會開啟遊戲視窗，檢查原生物理、轉向、煞車、跳躍、暫停、重生、檢查點、完賽、最佳紀錄、鏡頭切換與畫布縮放，並繪製各種介面狀態。完成後會自動關閉視窗；成功時印出 `整合驗證通過` 並以代碼 0 結束，失敗則以非零代碼結束。

```powershell
& 'C:\Aquarius\AquariusDesktopVMREPL.exe' .\smoke.aqua
```

亦可在打包所有腳本後執行 `AquariusDesktopVMREPL.exe --entry smoke.rius .\marble_run.bottle`，驗證不依賴來源檔案的腳本瓶。

VM 套件必須包含符合其相依版本的 `System.Text.Json.dll`；若編譯腳本瓶時出現無法載入 `System.Text.Json, Version=9.0.0.0` 的錯誤，請使用相依套件完整的 VM 建置。

## 授權

本專案採用 [MIT 授權條款](LICENSE)。

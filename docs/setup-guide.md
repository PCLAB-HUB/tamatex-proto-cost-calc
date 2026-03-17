# tamatex 導入手順書

NAS上のExcelファイルをGoogle スプレッドシートへ自動同期するシステムの導入手順です。

---

## 目次

1. [前提条件](#1-前提条件)
2. [Google Cloud プロジェクトの準備](#2-google-cloud-プロジェクトの準備)
3. [Google Drive の準備](#3-google-drive-の準備)
4. [常時稼働PCへのインストール](#4-常時稼働pcへのインストール)
5. [NAS接続の確認](#5-nas接続の確認)
6. [設定ファイルの作成](#6-設定ファイルの作成)
7. [初回セットアップの実行](#7-初回セットアップの実行)
8. [動作確認](#8-動作確認)
9. [Windowsサービスとして常時実行する](#9-windowsサービスとして常時実行する)
10. [営業・役員へのスプレッドシート共有](#10-営業役員へのスプレッドシート共有)
11. [運用・トラブルシューティング](#11-運用トラブルシューティング)

---

## 1. 前提条件

以下が揃っていることを確認してください。

| 項目 | 要件 |
|------|------|
| 常時稼働PC | Windows 10/11、ネットワーク接続あり |
| Python | バージョン 3.11 以上 |
| QNAP NAS | PCからネットワークドライブとしてアクセス可能 |
| Google Workspace | 管理者権限を持つアカウント |
| インターネット | 常時接続（Google API通信用） |

### Python のインストール確認

コマンドプロンプトを開き、以下を実行します。

```
python --version
```

`Python 3.11.x` 以上が表示されればOKです。
表示されない場合は https://www.python.org/downloads/ からインストールしてください。

> インストール時に **「Add Python to PATH」にチェック** を入れてください。

---

## 2. Google Cloud プロジェクトの準備

Google Sheets API を利用するためにサービスアカウントを作成します。

### 2-1. Google Cloud Console にアクセス

1. ブラウザで https://console.cloud.google.com/ を開く
2. Google Workspace の管理者アカウントでログイン

### 2-2. プロジェクトの作成

1. 画面上部のプロジェクト選択ドロップダウンをクリック
2. 「新しいプロジェクト」をクリック
3. 以下を入力:
   - プロジェクト名: `tamatex`（任意の名前）
   - 組織: そのまま（自社ドメインが表示される場合はそのまま）
4. 「作成」をクリック
5. 作成完了後、そのプロジェクトが選択されていることを確認

### 2-3. API の有効化

2つのAPIを有効化します。

**Google Sheets API:**
1. 左メニュー「APIとサービス」→「ライブラリ」
2. 検索バーに `Google Sheets API` と入力
3. 「Google Sheets API」をクリック → 「有効にする」

**Google Drive API:**
1. ライブラリ画面に戻る
2. 検索バーに `Google Drive API` と入力
3. 「Google Drive API」をクリック → 「有効にする」

### 2-4. サービスアカウントの作成

1. 左メニュー「APIとサービス」→「認証情報」
2. 「＋認証情報を作成」→「サービスアカウント」
3. 以下を入力:
   - サービスアカウント名: `tamatex-sync`
   - サービスアカウントID: 自動入力される（例: `tamatex-sync@tamatex-xxxxx.iam.gserviceaccount.com`）
   - 説明: `Excel to Spreadsheet sync`（任意）
4. 「作成して続行」をクリック
5. ロールの選択は **スキップ**（「続行」をクリック）
6. 「完了」をクリック

### 2-5. JSONキーファイルのダウンロード

1. 作成したサービスアカウント `tamatex-sync` をクリック
2. 「キー」タブを開く
3. 「鍵を追加」→「新しい鍵を作成」
4. キーのタイプ: **JSON** を選択
5. 「作成」をクリック
6. JSONファイルが自動ダウンロードされる

> **重要**: このJSONファイルは認証情報です。第三者に渡さないでください。

7. ダウンロードしたファイルの名前を `service_account.json` に変更

### 2-6. サービスアカウントのメールアドレスを控える

ダウンロードしたJSONファイルをテキストエディタで開き、`client_email` の値を控えてください。

```json
{
  "client_email": "tamatex-sync@tamatex-xxxxx.iam.gserviceaccount.com",
  ...
}
```

この `tamatex-sync@tamatex-xxxxx.iam.gserviceaccount.com` を後の手順で使います。

---

## 3. Google Drive の準備

同期先のスプレッドシートを格納するフォルダを作成します。

### 3-1. 専用フォルダの作成

1. https://drive.google.com/ を開く
2. 「マイドライブ」または「共有ドライブ」内に新しいフォルダを作成
   - フォルダ名の例: `NAS同期データ`
3. 作成したフォルダを開く

### 3-2. フォルダIDの取得

フォルダを開いた状態で、ブラウザのアドレスバーを確認します。

```
https://drive.google.com/drive/folders/1ABCdefGHIjklMNOpqrSTUvwxYZ
                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                        この部分がフォルダID
```

`1ABCdefGHIjklMNOpqrSTUvwxYZ` の部分を控えてください。

### 3-3. サービスアカウントとフォルダを共有

1. フォルダを右クリック →「共有」
2. 手順 2-6 で控えたサービスアカウントのメールアドレスを入力
   - 例: `tamatex-sync@tamatex-xxxxx.iam.gserviceaccount.com`
3. 権限を **「編集者」** に設定
4. 「送信」をクリック

> この手順を行わないと、サービスアカウントがフォルダにファイルを作成できません。

---

## 4. 常時稼働PCへのインストール

### 4-1. プロジェクトファイルの配置

tamatex フォルダを常時稼働PCの任意の場所にコピーします。

```
推奨配置例: C:\tamatex\
```

### 4-2. サービスアカウントキーの配置

手順 2-5 でダウンロードした `service_account.json` を以下に配置します。

```
C:\tamatex\config\service_account.json
```

### 4-3. Python 仮想環境の作成と依存関係のインストール

コマンドプロンプトを **管理者として実行** し、以下を順に実行します。

```bat
cd C:\tamatex

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt
```

以下のようなメッセージが表示されれば成功です。

```
Successfully installed gspread-6.x.x google-auth-2.x.x openpyxl-3.x.x pyyaml-6.x.x ...
```

---

## 5. NAS接続の確認

### 5-1. ネットワークドライブの確認

エクスプローラーでNASのExcelファイルが保存されているフォルダにアクセスできることを確認します。

**ドライブレターでアクセスしている場合（推奨）:**
```
Z:\共有\Excel
```

**UNCパスでアクセスしている場合:**
```
\\192.168.1.100\shared\Excel
```

### 5-2. パスの確認方法

1. エクスプローラーでExcelファイルがあるフォルダを開く
2. アドレスバーをクリックしてフルパスをコピー
3. このパスを次の手順で使用

### 5-3. ドライブレター割り当て（UNCパスの場合）

UNCパスよりドライブレターの方が安定するため、ネットワークドライブの割り当てを推奨します。

1. エクスプローラーで「PC」を右クリック →「ネットワークドライブの割り当て」
2. ドライブレター（例: `Z:`）を選択
3. フォルダに NASのパスを入力（例: `\\192.168.1.100\shared`）
4. **「サインイン時に再接続する」にチェック**
5. 「完了」をクリック

> **重要**: 「サインイン時に再接続する」にチェックを入れないと、PC再起動後にドライブが切断されます。

---

## 6. 設定ファイルの作成

### 6-1. 設定ファイルのコピー

```bat
cd C:\tamatex
copy config\config.example.yaml config\config.yaml
```

### 6-2. 設定ファイルの編集

`config\config.yaml` をテキストエディタ（メモ帳等）で開き、以下を編集します。

```yaml
nas:
  # ★ 手順5で確認したNASパスを入力
  # Windowsパスの場合、バックスラッシュは二重にする
  base_path: "Z:\\共有\\Excel"
  file_patterns:
    - "*.xlsx"
  exclude_patterns:
    - "~$*"
    - "*.tmp"
    - ".~lock*"

google:
  # ★ サービスアカウントキーのパス（手順4-2で配置した場所）
  credentials_path: "./config/service_account.json"
  # ★ 手順3-2で控えたGoogle DriveフォルダID
  drive_folder_id: "1ABCdefGHIjklMNOpqrSTUvwxYZ"
  # ★ スプレッドシートを共有するメールアドレス
  share_with:
    - "eigyo@example.com"
    - "yakuin@example.com"
    - "shacho@example.com"

sync:
  # 同期間隔（分）
  interval_minutes: 15

logging:
  level: "INFO"
  file: "./logs/tamatex.log"
  max_size_mb: 10
  backup_count: 5
```

### 設定項目の説明

| 項目 | 説明 | 例 |
|------|------|-----|
| `nas.base_path` | NAS上のExcelフォルダのパス | `"Z:\\共有\\Excel"` |
| `nas.file_patterns` | 同期対象のファイルパターン | `["*.xlsx"]` |
| `nas.exclude_patterns` | 除外するファイルパターン | `["~$*", "*.tmp"]` |
| `google.credentials_path` | サービスアカウントJSONキーのパス | `"./config/service_account.json"` |
| `google.drive_folder_id` | 同期先のGoogle DriveフォルダID | `"1ABC..."` |
| `google.share_with` | 共有先メールアドレスのリスト | `["user@example.com"]` |
| `sync.interval_minutes` | 同期間隔（分） | `15` |
| `logging.level` | ログレベル（INFO / DEBUG / WARNING） | `"INFO"` |
| `logging.file` | ログファイルの出力先 | `"./logs/tamatex.log"` |

---

## 7. 初回セットアップの実行

NAS上のExcelファイルに対応するスプレッドシートを一括作成します。

### 7-1. 実行

```bat
cd C:\tamatex
.venv\Scripts\activate
python scripts\initial_setup.py
```

### 7-2. 期待される出力

```
2026-03-17 10:00:00 [INFO] tamatex - === 初回セットアップ開始 ===
2026-03-17 10:00:01 [INFO] tamatex - Google API認証成功
2026-03-17 10:00:02 [INFO] tamatex - スキャン完了: 15 ファイル検出 (Z:\共有\Excel)
2026-03-17 10:00:02 [INFO] tamatex - 検出ファイル: 15 個
2026-03-17 10:00:03 [INFO] tamatex - スプレッドシート作成: '[同期] 在庫表' (ID: xxxxxxxx)
2026-03-17 10:00:04 [INFO] tamatex - 共有追加: eigyo@example.com (閲覧者)
...
2026-03-17 10:01:00 [INFO] tamatex - === 初回セットアップ完了 ===
```

### 7-3. 確認

Google Drive の「NAS同期データ」フォルダを開き、`[同期] ファイル名` という名前のスプレッドシートが作成されていることを確認してください。

> この時点ではスプレッドシートは空です。次の手順で同期を実行するとデータが反映されます。

---

## 8. 動作確認

### 8-1. 手動で同期を実行

```bat
cd C:\tamatex
.venv\Scripts\activate
set PYTHONPATH=src
python -m tamatex.main
```

### 8-2. 期待される出力

```
2026-03-17 10:05:00 [INFO] tamatex - === tamatex 起動 (v0.1.0) ===
2026-03-17 10:05:00 [INFO] tamatex - NASパス: Z:\共有\Excel
2026-03-17 10:05:00 [INFO] tamatex - 同期間隔: 15分
2026-03-17 10:05:01 [INFO] tamatex - Google API認証成功
2026-03-17 10:05:01 [INFO] tamatex - --- 同期サイクル開始 ---
2026-03-17 10:05:02 [INFO] tamatex - スキャン完了: 15 ファイル検出 (Z:\共有\Excel)
2026-03-17 10:05:02 [INFO] tamatex - 新規ファイル: 15 件
2026-03-17 10:05:03 [INFO] tamatex - Excel読み取り開始: 在庫表.xlsx
2026-03-17 10:05:05 [INFO] tamatex -   シート更新: 'Sheet1' (500行 x 20列)
2026-03-17 10:05:06 [INFO] tamatex - 新規同期完了: 在庫表 → xxxxxxxx
...
2026-03-17 10:08:00 [INFO] tamatex - --- 同期サイクル完了: スキャン=15, 同期=15, エラー=0 ---
2026-03-17 10:08:00 [INFO] tamatex - 次回同期まで 15分 待機...
```

### 8-3. スプレッドシートの確認

1. Google Drive の「NAS同期データ」フォルダを開く
2. いずれかのスプレッドシートを開く
3. NAS上のExcelと同じデータが表示されていればOK

### 8-4. 更新の確認

1. NAS上のExcelファイルを開き、適当なセルを編集して保存
2. 15分後（次の同期サイクル）にスプレッドシートに反映されることを確認

### 8-5. 停止

コマンドプロンプトで `Ctrl + C` を押すと安全に停止します。

```
2026-03-17 10:20:00 [INFO] tamatex - シャットダウンシグナル受信 (signal=2)
2026-03-17 10:20:00 [INFO] tamatex - === tamatex 正常終了 ===
```

---

## 9. Windowsサービスとして常時実行する

動作確認が完了したら、PCを再起動しても自動で同期が続くようにサービス化します。

### 9-1. NSSM のインストール

1. https://nssm.cc/download にアクセス
2. 最新版をダウンロード（例: `nssm-2.24.zip`）
3. ZIPを展開し、`win64\nssm.exe` を `C:\tamatex\` にコピー

### 9-2. サービスの登録

コマンドプロンプトを **管理者として実行** し、以下を実行します。

```bat
cd C:\tamatex
nssm install tamatex
```

NSSM の設定画面が開きます。以下を入力してください。

**Application タブ:**

| 項目 | 値 |
|------|-----|
| Path | `C:\tamatex\.venv\Scripts\python.exe` |
| Startup directory | `C:\tamatex` |
| Arguments | `-m tamatex.main` |

**Environment タブ:**

| 項目 | 値 |
|------|-----|
| Environment variables | `PYTHONPATH=src` |

**Details タブ:**

| 項目 | 値 |
|------|-----|
| Display name | `tamatex - Excel Sync` |
| Description | `NAS Excel to Google Spreadsheet auto sync` |
| Startup type | `Automatic (Delayed Start)` |

> `Automatic (Delayed Start)` にすることで、PC起動時にネットワーク接続が確立されてからサービスが開始されます。

**Exit actions タブ:**

| 項目 | 値 |
|------|-----|
| Restart action | `Restart application` |
| Restart delay | `60000` (60秒) |

「Install service」をクリック。

### 9-3. サービスの開始

```bat
nssm start tamatex
```

### 9-4. サービスの状態確認

```bat
nssm status tamatex
```

`SERVICE_RUNNING` と表示されればOKです。

### よく使うサービス操作コマンド

| 操作 | コマンド |
|------|---------|
| 開始 | `nssm start tamatex` |
| 停止 | `nssm stop tamatex` |
| 再起動 | `nssm restart tamatex` |
| 状態確認 | `nssm status tamatex` |
| 設定変更 | `nssm edit tamatex` |
| サービス削除 | `nssm remove tamatex confirm` |

---

## 10. 営業・役員へのスプレッドシート共有

### 自動共有（推奨）

`config.yaml` の `share_with` にメールアドレスを記載すると、新しいスプレッドシート作成時に自動で共有されます。

```yaml
google:
  share_with:
    - "tanaka@example.com"
    - "suzuki@example.com"
    - "shacho@example.com"
```

### 手動共有

既に作成済みのスプレッドシートに後から共有を追加する場合は、Google Drive上で直接共有設定を行ってください。

1. Google Drive の「NAS同期データ」フォルダを開く
2. スプレッドシートを右クリック →「共有」
3. メールアドレスを入力 → 権限を「閲覧者」に設定 →「送信」

### 閲覧用URLの共有

営業・役員にはスプレッドシートのURLをブックマークしてもらいます。

1. スプレッドシートを開く
2. ブラウザのアドレスバーからURLをコピー
3. メールやチャットで共有

> URLは固定です。データが更新されても同じURLからアクセスできます。

---

## 11. 運用・トラブルシューティング

### ログの確認

ログファイルは以下に出力されます。

```
C:\tamatex\logs\tamatex.log
```

テキストエディタまたはコマンドプロンプトで確認できます。

```bat
type C:\tamatex\logs\tamatex.log
```

最新のログのみ確認する場合:
```bat
powershell Get-Content C:\tamatex\logs\tamatex.log -Tail 50
```

### よくあるエラーと対処法

#### 「設定ファイルが見つかりません」

```
FileNotFoundError: 設定ファイルが見つかりません: ./config/config.yaml
```

**原因:** `config/config.yaml` が作成されていない
**対処:** 手順6に従い `config.example.yaml` から `config.yaml` を作成

#### 「NASパスが見つかりません」

```
[ERROR] NASパスが見つかりません: Z:\共有\Excel
```

**原因:** NASのネットワークドライブが切断されている
**対処:**
1. エクスプローラーでNASにアクセスできるか確認
2. ネットワークドライブが切断されている場合は再接続
3. NAS本体の電源・ネットワーク接続を確認

#### 「Google API認証エラー」

```
google.auth.exceptions.DefaultCredentialsError: ...
```

**原因:** サービスアカウントのJSONキーファイルが正しくない
**対処:**
1. `config/service_account.json` が存在するか確認
2. ファイルの内容が正しいJSONか確認
3. 必要に応じて手順 2-5 でキーを再発行

#### 「Permission denied / 403 エラー」

```
gspread.exceptions.APIError: 403
```

**原因:** サービスアカウントにスプレッドシートまたはフォルダの権限がない
**対処:**
1. Google Drive上でフォルダがサービスアカウントと共有されているか確認（手順 3-3）
2. Google Sheets API / Drive API が有効になっているか確認（手順 2-3）

#### 「ファイル読み取りエラー（スキップ）」

```
[WARNING] ファイル読み取りエラー（スキップ）: Z:\...\file.xlsx - [Errno 13] Permission denied
```

**原因:** Excelファイルが別のユーザーによってロックされている可能性
**対処:** 通常は一時的な問題です。次の同期サイクル（15分後）で自動的に再試行されます。

#### 「同期が15分以上経っても始まらない」

**対処:**
1. サービスが動作しているか確認: `nssm status tamatex`
2. ログファイルを確認して最後の出力を確認
3. サービスを再起動: `nssm restart tamatex`

### Excelファイルの追加・削除

| 操作 | tamatexの動作 |
|------|---------------|
| NASに新しいExcelファイルを追加 | 次の同期サイクルで自動検知し、スプレッドシートを自動作成 |
| NASからExcelファイルを削除 | スプレッドシートはそのまま残る（データ保全のため） |
| Excelファイル名を変更 | 旧ファイルは削除扱い、新ファイル名でスプレッドシートが新規作成される |

### 設定変更後の反映

`config.yaml` を変更した場合は、サービスの再起動が必要です。

```bat
nssm restart tamatex
```

### 同期状態のリセット

全ファイルを強制的に再同期したい場合は、状態データベースを削除してサービスを再起動します。

```bat
nssm stop tamatex
del C:\tamatex\tamatex_state.db
nssm start tamatex
```

> スプレッドシートは削除されません。既存のスプレッドシートに上書き同期されます。
> ただし、マッピング情報が失われるため、新しいスプレッドシートが作成されます。
> 古いスプレッドシートは手動でGoogle Driveから削除してください。

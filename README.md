# README
## クイックスタート（通し手順）

```
# 1. 仮想環境の作成と有効化
python -m venv venv
source venv/Scripts/activate

# 2. 依存関係のインストール
pip install -r requirements.txt
```

## 依存関係 (Requirements) について

このプロジェクトの依存関係は、`pip-tools` を使用して管理しています。  
`pip-tools` をインストールしてください。  

```
pip install pip-tools
```

※`pip-tools`は、グローバルインストールを推奨します。  

### パッケージの更新とインストール

* **新しいパッケージの追加:** 
    `requirements.in` に追加したいパッケージ名を追記してください。
* **依存関係の更新:** 
    `requirements.in` に基づいて、依存パッケージを最新版に更新するには、以下のコマンドを実行します。
    ```
    pip-compile --upgrade requirements.in
    ```
* **環境へのインストール:**
    `requirements.txt` に記載されたパッケージをインストールするには、以下のコマンドを実行します。
    ```
    pip install -r requirements.txt
    ```
    ※開発時は仮想環境へのインストールをしてください。

* **コミット時の注意点:**
    `requirements.in` を更新した際は、`pip-compile` を実行して `requirements.txt` を更新し、**両方のファイルをセットでコミットしてください。**

## venv の利用について
Pythonの仮想環境 venvを利用して開発をしています。  
本番・テスト・開発に分類的な名称をつけて環境を切り替えて開発を行っています。  
開発時は仮想環境を利用してください。  

### venv 仮想環境の作成の仕方

下記コマンドで仮想環境を作成できます。  
（backend ディレクトリにて行う）  

```shell
python -m venv venv
```

### venv の開始について
シェルに応じて下記コマンドを実行することで、仮想環境に切り替えることができます。

**Windows (コマンドプロンプト)**
```shell
venv\Scripts\activate.bat
```

**Windows (PowerShell)**
```shell
venv\Scripts\Activate.ps1
```

**Git Bash（Windows）**
```shell
source venv/Scripts/activate
```

ターミナル等で仮想環境が有効化されているかを確認できます。  

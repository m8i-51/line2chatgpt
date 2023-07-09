# README

自分の趣味界隈にChatGPTの凄さを知ってもらうために始めた個人PJです。

粗々ですが、個人なのでご愛嬌

プルリク大歓迎です。待ってます。

## 開発環境/ツール

* MacBook Pro (13-inch, 2019, Four Thunderbolt 3 ports)
* macOS Ventura 13.4.1（22F82）
* VScode
* Serverless Framework v3.30.1
* rye v0.7.0(PythonのPJ管理ツール)

## 参考にさせていただいたサイト様

[Serverless Frameworkの使い方まとめ](https://serverless.co.jp/blog/25/)

[Serverless FrameworkとAWS Lambda with Pythonの環境にpipインストール](https://qiita.com/suzuki-navi/items/b5f513f21d37365c248f)

[久しぶりのPython環境をRyeで整える](https://zenn.dev/watany/articles/f69db9e33d4427)

[【python】LINE botの作り方(Messaging API)](https://junpage.com/line-bot-development/)

[ServerlessFrameworkを使ってChatGPT APIを使ったLineBotを作る](https://synamon.hatenablog.com/entry/openai_api_linebot)

## 環境

![](AWS.drawio.svg)

## ポイント

* Serverless Frameworkのプラグイン(`serverless-python-requirements`)を利用してます
* ryeはめちゃくちゃ便利だけど、業務で利用するのは正直微妙。なぜかは[コチラ](https://nsakki55.hatenablog.com/entry/2023/05/29/013658)

## 課題

* Windows環境はよくわからん
> 誰か検証＆FBして欲しい
* メッセージ暗号化しないとまずい
* 自動でデプロイさせたい

import openai
import streamlit as st
import ffmpeg
import os
import subprocess
import tempfile
import tiktoken

#トークン数カウント
def count_tokens(text: str, model_name: str) -> int:
    encoding = tiktoken.encoding_for_model(model_name)
    num_tokens = len(encoding.encode(text))
    return num_tokens

# ユーザーインターフェイスの構築
st.title("議事録作成アプリ")
st.write("録画ファイルから議事録を自動生成する。")

# OpenAI API Keyの取得
user_api_key = st.sidebar.text_input("OpenAI API Keyを入力してください。", key="user_api_key", type="password")
openai.api_key = user_api_key

# ボタンの有効/無効状態を管理する変数を初期化する
file_uploader_disabled = True
# OpenAI API Keyが入力された場合にボタンを有効にする
if user_api_key:
    file_uploader_disabled = False

#ファイルアップロード
uploaded_file = st.sidebar.file_uploader("動画ファイルをアップロードしてください", type=["mp4"], disabled=file_uploader_disabled)

if uploaded_file is not None:
    # video_bytesを一時ファイルに保存
    tmp_dir = tempfile.TemporaryDirectory()
    tmp_file_path = f"{tmp_dir.name}/input.mp4"
    with open(tmp_file_path, "wb") as tmp_file:
        tmp_file.write(audio_file.read())

    # ffmpeg-pythonを使用して音声を抽出してMP3に変換
    audio_path = f"{tmp_dir.name}/output.mp3"
    with st.spinner("音声抽出中..."):
        cmd = f"ffmpeg -i {tmp_file_path} -ac 1 -ar 16000 {audio_path}"
        subprocess.run(cmd, shell=True)

        st.success("音声の抽出が完了しました。")

    # 抽出された音声からWhisperを使って文字起こし
    with st.spinner("テキストを生成中..."):
        with open(audio_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)

        st.success("文字起こしが完了しました。")
        st.write(transcript.text)

    # 議事録生成
    prompt = f"""
    会議の録画ファイルの文字起こしテキストを元に、議事録を作成します。以下は主な議論や決定事項です。

    会議日時: [日付]
    会議場所: [場所]
    参加者: [参加者の名前]
    [議論の要点]

    [重要な決定事項]

    [アクションアイテム]

    ---
    以上が議事録の要点です。詳細な内容については、以下の「」内テキストを参照してください。
    なお、議論の要点、重要な決定事項、アクションアイテムは複数存在する場合がありますので、そちらも注意してください。
    ---

    「{transcript.text}」
    """

    #トークン数によって使用するモデルを決定する
    token_count = count_tokens(transcript.text, "gpt-3.5-turbo")
    if token_count >= 3000:
        use_model = "gpt-3.5-turbo-16k"
    else:
        use_model = "gpt-3.5-turbo"

    with st.spinner("議事録を生成中..."):
        response = openai.ChatCompletion.create(
        model=use_model,
        messages=[
              {"role": "user", "content": prompt}
          ]
        )

        st.subheader("議事録")
        st.write(response["choices"][0]["message"]['content'])

    # 一時ファイルの削除
    os.remove(tmp_file_path)
    os.remove(audio_path)

import aiofiles
import aiohttp
import urllib.parse


class TTSAPI:

    voices = {
        "clara": {"language": "english", "gender": "female"},
        "matt": {"language": "english", "gender": "male"},
        "carmen": {"language": "spanish", "gender": "female"},
        "jose": {"language": "spanish", "gender": "male"},
        "shinji": {"language": "japanese", "gender": "male"},
        "kyuri": {"language": "korean", "gender": "female"},
        "jinho": {"language": "korean", "gender": "male"},
        "meimei": {"language": "chinese", "gender": "female"},
        "liangliang": {"language": "chinese", "gender": "male"},
    }

    speeds = {0: 5, 1: 4, 2: 3, 3: 2, 4: 1, 5: 0, 6: -1, 7: -2, 8: -3, 9: -4, 10: -5}

    async def get_audio(self, text, voice, speed, file):
        session = aiohttp.ClientSession()
        wrapped_text = urllib.parse.quote(text)
        async with session.get(
            f"https://dict.naver.com/api/nvoice?service=dictionary&speech_fmt=mp3&text={wrapped_text}&speaker={voice}&speed={speed}"
        ) as request:
            f = await aiofiles.open(file, mode="wb")
            await f.write(await request.read())
            await f.close()
        await session.close()

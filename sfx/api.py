import aiofiles
import aiohttp
import urllib.parse


class TTSAPI:

    voices = {
        "clara": {"language": "english", "gender": "female", "limit": 600},
        "matt": {"language": "english", "gender": "male", "limit": 500},
        "carmen": {"language": "spanish", "gender": "female", "limit": 500},
        "jose": {"language": "spanish", "gender": "male", "limit": 500},
        "shinji": {"language": "japanese", "gender": "male", "limit": 200},
        "kyuri": {"language": "korean", "gender": "female", "limit": 250},
        "jinho": {"language": "korean", "gender": "male", "limit": 250},
        "meimei": {
            "language": "chinese (simplified)",
            "gender": "female",
            "limit": 200,
        },
        "liangliang": {"language": "chinese", "gender": "male", "limit": 150},
        "chiahua": {
            "language": "chinese (traditional)",
            "gender": "female",
            "limit": 150,
        },
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

from os.path import isfile
from aiosqlite import connect

class DBInterface():
    async def connect(self, cwd):
        self.DB_PATH = f"{cwd}/data/database.db"
        self.BUILD_PATH = f"{cwd}/data/build.sql"

        self.cxn = await connect(self.DB_PATH, check_same_thread=False)
        self.cur = await self.cxn.cursor()

    async def build(self):
        if isfile(self.BUILD_PATH):
            await self.scriptexec(self.BUILD_PATH)
        await self.commit()

    async def commit(self):
        await self.cxn.commit()

    async def close(self):
        await self.cxn.close()

    async def field(self, command, *values):
        await self.cur.execute(command, tuple(values))
        if (fetch := await self.cur.fetchone()) is not None:
            return fetch[0]

    async def record(self, command, *values):
        await self.cur.execute(command, tuple(values))

        return await self.cur.fetchone()

    async def records(self, command, *values):
        await self.cur.execute(command, tuple(values))

        return await self.cur.fetchall()

    async def column(self, command, *values):
        await self.cur.execute(command, tuple(values))

        return [item[0] for item in await self.cur.fetchall()]

    async def execute(self, command, *values):
        await self.cur.execute(command, tuple(values))

    async def multiexec(self, command, valueset):
        await self.cur.execute(command, valueset)

    async def scriptexec(self, path):
        with open(path, "r", encoding="utf-8") as script:
            await self.cur.executescript(script.read())
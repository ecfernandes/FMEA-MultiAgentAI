import asyncio
import asyncpg

async def check_tables():
    conn = await asyncpg.connect('postgresql://fmea:fmea_secret@localhost:5433/fmea_db')
    
    tables = await conn.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
    )
    
    print('\nTabelas criadas no PostgreSQL:\n')
    for t in tables:
        print(f'  - {t["tablename"]}')
    
    print(f'\nTotal: {len(tables)} tabelas\n')
    
    await conn.close()

asyncio.run(check_tables())

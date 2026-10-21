"""Repeatable starter vocabulary for games; never overwrite existing content."""
from sqlalchemy import text
from app.core.database import engine

# 20 words per topic, enough for five full random rounds on a fresh database.
DATA = {
 'animals': "cat:con mèo|dog:con chó|bird:con chim|fish:con cá|horse:con ngựa|cow:con bò|pig:con lợn|duck:con vịt|chicken:con gà|sheep:con cừu|goat:con dê|rabbit:con thỏ|mouse:con chuột|elephant:con voi|tiger:con hổ|lion:con sư tử|monkey:con khỉ|bear:con gấu|snake:con rắn|frog:con ếch",
 'food': "apple:quả táo|banana:quả chuối|orange:quả cam|grape:quả nho|lemon:quả chanh vàng|mango:quả xoài|bread:bánh mì|rice:cơm|noodle:mì sợi|egg:quả trứng|milk:sữa|water:nước|juice:nước ép|tea:trà|coffee:cà phê|cake:bánh ngọt|cheese:phô mai|potato:khoai tây|tomato:cà chua|carrot:cà rốt",
 'objects': "book:quyển sách|pen:bút mực|pencil:bút chì|bag:cái túi|table:cái bàn|chair:cái ghế|door:cánh cửa|window:cửa sổ|bed:cái giường|clock:đồng hồ|phone:điện thoại|computer:máy tính|car:ô tô|bus:xe buýt|bike:xe đạp|hat:cái mũ|shirt:áo sơ mi|shoe:chiếc giày|key:chìa khóa|bottle:cái chai",
 'places': "school:trường học|hospital:bệnh viện|market:chợ|bank:ngân hàng|park:công viên|library:thư viện|restaurant:nhà hàng|hotel:khách sạn|airport:sân bay|station:nhà ga|beach:bãi biển|farm:nông trại|zoo:sở thú|museum:bảo tàng|cinema:rạp chiếu phim|shop:cửa hàng|kitchen:nhà bếp|bedroom:phòng ngủ|garden:khu vườn|street:đường phố",
 'nature': "sun:mặt trời|moon:mặt trăng|star:ngôi sao|sky:bầu trời|cloud:đám mây|rain:mưa|wind:gió|snow:tuyết|tree:cây|flower:bông hoa|leaf:chiếc lá|grass:cỏ|river:dòng sông|lake:hồ nước|sea:biển|mountain:ngọn núi|forest:khu rừng|island:hòn đảo|stone:hòn đá|sand:cát",
}

def main():
    created=0
    with engine.begin() as connection:
        # Serialize repeat runs so two seed processes cannot race on vocabulary.word.
        connection.execute(text("SELECT pg_advisory_xact_lock(771006)"))
        for slug,entries in DATA.items():
            topic=connection.scalar(text("SELECT topic_id FROM topics WHERE slug=:slug"),{'slug':slug})
            if topic is None: raise RuntimeError("Run alembic upgrade head first")
            for entry in entries.split('|'):
                word,meaning=entry.split(':',1)
                ident=connection.scalar(text("SELECT vocabulary_id FROM vocabularies WHERE lower(word)=:word ORDER BY vocabulary_id LIMIT 1"),{'word':word})
                if ident is None:
                    ident=connection.scalar(text("INSERT INTO vocabularies(word,level) VALUES(:word,'BEGINNER') RETURNING vocabulary_id"),{'word':word})
                    connection.execute(text("INSERT INTO vocabulary_meanings(vocabulary_id,meaning_vi) VALUES(:id,:meaning)"),{'id':ident,'meaning':meaning})
                    created+=1
                connection.execute(text("INSERT INTO vocabulary_topics(topic_id,vocabulary_id) VALUES(:t,:v) ON CONFLICT DO NOTHING"),{'t':topic,'v':ident})
    print(f"Created {created} starter words; existing words and meanings preserved.")

if __name__=='__main__': main()

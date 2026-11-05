from email.mime.text import MIMEText

from newsbot.db import Database
from newsbot.mail import Vault, fetch_new, find_embargo, parse_message


def raw_mail(subject, body):
    m = MIMEText(body, "plain", "utf-8")
    m["Subject"] = subject
    m["From"] = "홍보팀 <pr@example.com>"
    m["Date"] = "Wed, 05 Nov 2026 09:00:00 +0900"
    return m.as_bytes()


def test_parse_and_embargo():
    m = parse_message(raw_mail("[보도자료] 신약 허가", "엠바고: 11월 6일(목) 12시 이후 보도\n본문입니다"))
    assert m["subject"] == "[보도자료] 신약 허가"
    assert m["embargo"].startswith("엠바고: 11월 6일")
    assert m["sent_at"].startswith("2026-11-05T09:00")
    assert find_embargo("일반 메일", "내용") == ""


class FakeIMAP:
    def __init__(self, host):
        self.host, self.readonly = host, None
        self.mails = {5: raw_mail("자료1", "본문1"), 6: raw_mail("자료2", "보도시점: 즉시")}

    def login(self, u, p):
        assert p == "app-password"

    def select(self, folder, readonly=False):
        self.readonly = readonly
        assert readonly, "읽기 전용으로 열어야 함"
        return "OK", [b"2"]

    def uid(self, cmd, *args):
        if cmd == "search":
            return "OK", [b" ".join(str(u).encode() for u in self.mails)]
        uid = int(args[0])
        assert args[1] == "(BODY.PEEK[])"
        return "OK", [(b"1 (BODY[] {10}", self.mails[uid]), b")"]

    def logout(self):
        pass


def test_fetch_new_readonly(tmp_path):
    db = Database(":memory:")
    db.execute("INSERT INTO users(id, username, display_name, pw_hash, created_at) VALUES(1,'a','A','x','t')")
    v = Vault(tmp_path)
    db.execute("INSERT INTO mail_accounts(user_id, host, username, secret_enc, folder, updated_at) VALUES(1,'h','u',?,'보도자료','t')",
               (v.seal("app-password"),))
    acc = db.one("SELECT * FROM mail_accounts WHERE user_id=1")
    assert fetch_new(db, v, acc, imap_factory=FakeIMAP) == 2
    assert db.one("SELECT last_uid FROM mail_accounts")["last_uid"] == 6
    assert db.one("SELECT embargo FROM mails WHERE uid=6")["embargo"].startswith("보도시점")
    acc = db.one("SELECT * FROM mail_accounts WHERE user_id=1")
    assert fetch_new(db, v, acc, imap_factory=FakeIMAP) == 0  # 다시 받아도 중복 없음

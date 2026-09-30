"""
[참고] 키움 REST API 버전 최소 예제 (64bit / OS 무관)
엔드포인트·api-id·필드명은 반드시 https://openapi.kiwoom.com 공식 문서로 확인 후 사용하세요.
"""
import requests

HOST = "https://mockapi.kiwoom.com"   # 실전: https://api.kiwoom.com


class KiwoomREST:
    def __init__(self, appkey: str, secretkey: str):
        self.appkey, self.secretkey = appkey, secretkey
        self.token = self._issue_token()

    def _issue_token(self) -> str:
        r = requests.post(f"{HOST}/oauth2/token", json={
            "grant_type": "client_credentials",
            "appkey": self.appkey, "secretkey": self.secretkey})
        r.raise_for_status()
        return r.json()["token"]

    def call(self, path: str, api_id: str, body: dict, cont_yn="N", next_key=""):
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {self.token}",
            "api-id": api_id, "cont-yn": cont_yn, "next-key": next_key,
        }
        r = requests.post(f"{HOST}{path}", headers=headers, json=body)
        r.raise_for_status()
        return r.json(), r.headers.get("cont-yn"), r.headers.get("next-key")


if __name__ == "__main__":
    api = KiwoomREST("APP_KEY", "SECRET_KEY")
    data, *_ = api.call("/api/dostk/stkinfo", "ka10001", {"stk_cd": "005930"})  # 주식기본정보
    print(data)

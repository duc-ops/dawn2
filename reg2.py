import concurrent.futures
import random
import string
import time
import requests
from typing import List, Optional, Tuple, Dict

BASE_URL = "https://api.mail.tm"
OUTPUT_FILE = "email_accounts.txt"
PROXY_FILE = "proxy.txt"

# ------------ Proxy helpers ------------
def load_proxy_lines(path: str = PROXY_FILE) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    except FileNotFoundError:
        return []


def build_requests_proxies(proxy_line: Optional[str]) -> Optional[Dict[str, str]]:
    if not proxy_line:
        return None
    # requests chấp nhận dict với cả http và https
    return {"http": proxy_line, "https": proxy_line}


# ------------ API helpers ------------
def get_domains(proxies: Optional[Dict[str, str]] = None) -> List[str]:
    resp = requests.get(f"{BASE_URL}/domains", proxies=proxies, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    members = data.get("hydra:member", [])
    return [m.get("domain") for m in members if m.get("domain")]


def create_account(address: str, password: str, proxies: Optional[Dict[str, str]] = None) -> None:
    payload = {"address": address, "password": password}
    resp = requests.post(f"{BASE_URL}/accounts", json=payload, proxies=proxies, timeout=20)
    resp.raise_for_status()


def get_token(address: str, password: str, proxies: Optional[Dict[str, str]] = None) -> str:
    payload = {"address": address, "password": password}
    resp = requests.post(f"{BASE_URL}/token", json=payload, proxies=proxies, timeout=20)
    resp.raise_for_status()
    return resp.json().get("token", "")


# ------------ Generator ------------
def random_string(n: int = 10) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choice(alphabet) for _ in range(n))


def generate_one(domains: List[str], proxy_lines: List[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Trả về tuple (email, password, token, error)
    Nếu lỗi, 3 giá trị đầu sẽ là None và error có thông báo lỗi.
    """
    try:
        # Chọn proxy ngẫu nhiên cho request này
        proxy_line = random.choice(proxy_lines) if proxy_lines else None
        proxies = build_requests_proxies(proxy_line)

        # Để hạn chế vượt 8 QPS/IP: thêm trễ ngẫu nhiên nhỏ
        time.sleep(random.uniform(0.15, 0.35))

        # Lấy domain (dùng danh sách đã truyền vào)
        if not domains:
            # Nếu không có domains sẵn, thử load 1 lần với proxy hiện tại
            domains_local = get_domains(proxies)
            if not domains_local:
                return None, None, None, "Không lấy được domain"
            domain = random.choice(domains_local)
        else:
            domain = random.choice(domains)

        username = f"phanhxinh{random_string(6)}{random.randint(1000,9999)}"
        password = f"{random_string(8)}{random.randint(1000,9999)}"
        address = f"{username}@{domain}"

        # Tạo account
        create_account(address, password, proxies)

        # Lấy token
        token = get_token(address, password, proxies)
        if not token:
            return None, None, None, "Không lấy được token"

        # Lưu file theo định dạng yêu cầu
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(f"{address}|{password}|{token}\n")

        return address, password, token, None

    except requests.exceptions.HTTPError as he:
        return None, None, None, f"HTTPError: {he}"
    except requests.exceptions.RequestException as re:
        return None, None, None, f"RequestException: {re}"
    except Exception as e:
        return None, None, None, f"Lỗi: {e}"


def download_free_proxies() -> List[str]:
    print("Đang tải free proxy từ GitHub...")
    urls = [
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/https.txt",
    ]
    all_proxies = []
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            all_proxies.extend([ln.strip() for ln in response.text.splitlines() if ln.strip()])
        except requests.exceptions.RequestException as e:
            print(f"Lỗi khi tải proxy từ {url}: {e}")
    print(f"Đã tải về {len(all_proxies)} free proxy.")
    return all_proxies


def main():
    # Hỏi số lượng mail
    while True:
        try:
            num_emails = int(input("Bạn muốn tạo bao nhiêu mail? ").strip())
            if num_emails <= 0:
                print("Số lượng mail phải lớn hơn 0.")
                continue
            break
        except ValueError:
            print("Vui lòng nhập một số hợp lệ.")

    # Hỏi số luồng
    while True:
        try:
            num_threads = int(input("Bạn muốn chạy mấy luồng (1-50)? ").strip())
            if not (1 <= num_threads <= 50):
                print("Số luồng phải nằm trong khoảng từ 1 đến 50.")
                continue
            break
        except ValueError:
            print("Vui lòng nhập một số hợp lệ.")

    # Hỏi người dùng loại proxy muốn sử dụng
    while True:
        proxy_choice = input("Bạn muốn sử dụng private proxy (1) hay free proxy (2)? ").strip()
        if proxy_choice == '1':
            proxy_lines = load_proxy_lines(PROXY_FILE)
            if not proxy_lines:
                print("Không tìm thấy private proxy trong file proxy.txt. Vui lòng kiểm tra lại.")
                continue
            break
        elif proxy_choice == '2':
            proxy_lines = download_free_proxies()
            if not proxy_lines:
                print("Không tải được free proxy. Vui lòng thử lại sau.")
                continue
            break
        else:
            print("Lựa chọn không hợp lệ. Vui lòng nhập 1 hoặc 2.")

    # Lấy domain 1 lần (không dùng proxy để có tỉ lệ thành công cao), nếu thất bại sẽ fallback từng luồng
    try:
        domains = get_domains(None)
    except Exception:
        domains = []

    print(f"Bắt đầu tạo {num_emails} email với {num_threads} luồng...")
    success = 0
    errors = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(generate_one, domains, proxy_lines) for _ in range(num_emails)]
        for fut in concurrent.futures.as_completed(futures):
            email, password, token, err = fut.result()
            if err:
                errors += 1
                print(f"[LỖI] {err}")
            else:
                success += 1
                print(f"[OK] {email}")

    print(f"Hoàn tất. Thành công: {success}, Lỗi: {errors}. Kết quả nằm trong {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
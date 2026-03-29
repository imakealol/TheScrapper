import json
from argparse import ArgumentParser, Namespace
from pathlib import Path

import requests

from modules.info_reader import InfoReader
from modules.scrapper import Scrapper

BANNER: str = """
▄▄▄█████▓ ██░ ██ ▓█████   ██████  ▄████▄   ██▀███   ▄▄▄       ██▓███   ██▓███  ▓█████  ██▀███  
▓  ██▒ ▓▒▓██░ ██▒▓█   ▀ ▒██    ▒ ▒██▀ ▀█  ▓██ ▒ ██▒▒████▄    ▓██░  ██▒▓██░  ██▒▓█   ▀ ▓██ ▒ ██▒
▒ ▓██░ ▒░▒██▀▀██░▒███   ░ ▓██▄   ▒▓█    ▄ ▓██ ░▄█ ▒▒██  ▀█▄  ▓██░ ██▓▒▓██░ ██▓▒▒███   ▓██ ░▄█ ▒
░ ▓██▓ ░ ░▓█ ░██ ▒▓█  ▄   ▒   ██▒▒▓▓▄ ▄██▒▒██▀▀█▄  ░██▄▄▄▄██ ▒██▄█▓▒ ▒▒██▄█▓▒ ▒▒▓█  ▄ ▒██▀▀█▄  
  ▒██▒ ░ ░▓█▒░██▓░▒████▒▒██████▒▒▒ ▓███▀ ░░██▓ ▒██▒ ▓█   ▓██▒▒██▒ ░  ░▒██▒ ░  ░░▒████▒░██▓ ▒██▒
  ▒ ░░    ▒ ░░▒░▒░░ ▒░ ░▒ ▒▓▒ ▒ ░░ ░▒ ▒  ░░ ▒▓ ░▒▓░ ▒▒   ▓▒█░▒▓▒░ ░  ░▒▓▒░ ░  ░░░ ▒░ ░░ ▒▓ ░▒▓░
    ░     ▒ ░▒░ ░ ░ ░  ░░ ░▒  ░ ░  ░  ▒     ░▒ ░ ▒░  ▒   ▒▒ ░░▒ ░     ░▒ ░      ░ ░  ░  ░▒ ░ ▒░
  ░       ░  ░░ ░   ░   ░  ░  ░  ░          ░░   ░   ░   ▒   ░░       ░░          ░     ░░   ░ 
          ░  ░  ░   ░  ░      ░  ░ ░         ░           ░  ░                     ░  ░   ░     
                                 ░                                                            
"""


def build_parser() -> ArgumentParser:
    p = ArgumentParser(description="TheScrapper - Contact finder")
    p.add_argument("-u",   "--url",            help="Target URL.")
    p.add_argument("-us",  "--urls",           help="File containing target URLs (one per line).")
    p.add_argument("-c",   "--crawl",          action="store_true", help="Crawl every URL found on the site.")
    p.add_argument("-b",   "--banner",         action="store_true", help="Suppress the banner.")
    p.add_argument("-e",   "--email",          action="store_true", help="Extract email addresses.")
    p.add_argument("-n",   "--number",         action="store_true", help="Extract phone numbers.")
    p.add_argument("-s",   "--socials",        action="store_true", help="Extract and print social media links.")
    p.add_argument("--social-extract",         action="store_true", help="Fetch detailed info for found social media links (implies --socials).")
    p.add_argument("-o",   "--output",         action="store_true", help="Save output to a JSON file.")
    p.add_argument("-v",   "--verbose",        action="store_true", help="Verbose output.")
    return p


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "http://" + url
    return url


def scrape(url: str, args: Namespace) -> dict:
    """Scrape a single URL and return structured results."""
    scrap = Scrapper(url=url, crawl=args.crawl)
    ir = InfoReader(content=scrap.getText())

    extract_contacts = not args.email and not args.number and not args.socials
    want_sm = args.socials or args.social_extract

    result: dict = {"Target": url}

    if args.email or extract_contacts:
        result["E-Mails"] = ir.getEmails()
    if args.number or extract_contacts:
        result["Numbers"] = ir.getPhoneNumber()
    if want_sm or extract_contacts:
        result["SocialMedia"] = ir.getSocials()

    return result


def print_result(result: dict, args: Namespace) -> None:
    print("*" * 50)
    print(f"Target: {result['Target']}")
    print("*" * 50 + "\n")

    if "E-Mails" in result:
        emails = result["E-Mails"]
        print("E-Mails:\n" + ("\n - ".join(emails) if emails else "  (none)"))

    if "Numbers" in result:
        numbers = result["Numbers"]
        print("Numbers:\n" + ("\n - ".join(numbers) if numbers else "  (none)"))

    if "SocialMedia" in result:
        sm = result["SocialMedia"]
        if args.social_extract:
            ir = InfoReader(content=Scrapper(url=result["Target"], crawl=False).getText())
            print("SocialMedia:")
            for entry in ir.getSocialsInfo():
                sm_url, info = entry["url"], entry["info"]
                if info:
                    print(f" - {sm_url}:")
                    for k, v in info.items():
                        print(f"     - {k}: {v}")
                else:
                    print(f" - {sm_url}")
        else:
            print("SocialMedia: " + (", ".join(sm) if sm else "(none)"))

    print()


def save_output(data: dict | list, name: str) -> None:
    Path("output").mkdir(exist_ok=True)
    file_name = name.lower().replace("http://", "").replace("https://", "").replace("/", "")
    out_path = Path("output") / f"{file_name}.json"
    out_path.write_text(json.dumps(data, indent=4))
    print(f"Saved → {out_path}")


def main() -> None:
    args = build_parser().parse_args()

    if not args.url and not args.urls:
        raise SystemExit("Please add --url or --urls")

    if not args.banner:
        print(BANNER)

    verbose = print if args.verbose else lambda *_: None

    if args.url:
        url = normalize_url(args.url)
        requests.get(url)
        verbose("Scraping started")
        result = scrape(url, args)
        verbose("Done")
        print_result(result, args)
        if args.output:
            save_output(result, url)

    else:
        results = []
        for raw in Path(args.urls).read_text().splitlines():
            url = normalize_url(raw.strip())
            if not url:
                continue
            requests.get(url)
            verbose(f"Scraping {url}")
            result = scrape(url, args)
            verbose("Done")
            print_result(result, args)
            results.append(result)

        if args.output:
            save_output(results, args.urls.replace("/", "_"))


if __name__ == "__main__":
    main()
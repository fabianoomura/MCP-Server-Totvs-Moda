"""
Decodifica XML de NF-e base64 retornado pela API TOTVS.

Uso:
  python decode_xml.py <base64_string>              # imprime no terminal
  python decode_xml.py <base64_string> -o nfe.xml   # salva em arquivo
  python decode_xml.py -f arquivo_b64.txt           # lê base64 de arquivo
"""
import argparse
import base64
import sys
import xml.dom.minidom


def decode_nfe(b64: str) -> str:
    raw = base64.b64decode(b64).decode("utf-8")
    return xml.dom.minidom.parseString(raw).toprettyxml(indent="  ")


def main():
    p = argparse.ArgumentParser(description="Decodifica XML NF-e base64")
    p.add_argument("base64", nargs="?", help="String base64 direta")
    p.add_argument("-f", "--file", help="Arquivo com base64")
    p.add_argument("-o", "--output", help="Salvar XML em arquivo")
    p.add_argument("--raw", action="store_true", help="Sem pretty-print")
    args = p.parse_args()

    if args.file:
        with open(args.file, "r") as fh:
            b64 = fh.read().strip()
    elif args.base64:
        b64 = args.base64.strip()
    else:
        b64 = sys.stdin.read().strip()

    if args.raw:
        xml_str = base64.b64decode(b64).decode("utf-8")
    else:
        xml_str = decode_nfe(b64)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(xml_str)
        print(f"Salvo em {args.output} ({len(xml_str)} bytes)")
    else:
        print(xml_str)


if __name__ == "__main__":
    main()

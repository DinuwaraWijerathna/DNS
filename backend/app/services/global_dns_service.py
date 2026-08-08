import dns.resolver


def domain_exists_globally(domain: str) -> bool:
    record_types = ["A", "AAAA", "CNAME", "MX", "NS"]

    for record_type in record_types:
        try:
            dns.resolver.resolve(domain, record_type)
            return True
        except Exception:
            continue

    return False
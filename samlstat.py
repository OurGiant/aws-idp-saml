#!/usr/bin/env python3
"""
samlstat - CLI tool to display AWS SAML credential status and authenticate.

Shows the same info as the aws-idp-saml-ui Java desktop app:
  - Profile names from ~/.aws/samlsts
  - Credential status from ~/.aws/credentials
  - Token expiration from ~/.aws/aws_saml.db

Authentication uses the existing aws-idp-saml getCredentials flow.
"""

import argparse
import configparser
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


# --- ANSI color codes ---

class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"


def supports_color() -> bool:
    """Check if the terminal supports color output."""
    if os.environ.get("NO_COLOR"):
        return False
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    return True


class NoColor:
    """Fallback when color is disabled."""
    RESET = ""
    BOLD = ""
    DIM = ""
    GREEN = ""
    RED = ""
    YELLOW = ""
    CYAN = ""
    WHITE = ""


# --- Data loading ---

def get_aws_dir() -> Path:
    return Path.home() / ".aws"


def load_samlsts_profiles(aws_dir: Path) -> list[str]:
    """Load profile names from ~/.aws/samlsts (excluding Fed-* and global sections)."""
    config_path = aws_dir / "samlsts"
    if not config_path.exists():
        return []

    config = configparser.ConfigParser()
    config.read(str(config_path))

    profiles = []
    for section in config.sections():
        if not section.startswith("Fed-") and section.lower() != "global":
            profiles.append(section)

    return sorted(profiles, key=str.lower)


def load_credentials_profiles(aws_dir: Path) -> set[str]:
    """Load profile names from ~/.aws/credentials."""
    creds_path = aws_dir / "credentials"
    if not creds_path.exists():
        return set()

    config = configparser.ConfigParser()
    config.read(str(creds_path))
    return set(config.sections())


def load_token_expirations(aws_dir: Path) -> dict[str, datetime]:
    """Load token expirations from ~/.aws/aws_saml.db SQLite database."""
    db_path = aws_dir / "aws_saml.db"
    if not db_path.exists():
        return {}

    expirations = {}
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT profile_name, expiration FROM token_state")
        for row in cursor:
            profile_name, expiration_str = row
            try:
                exp = datetime.fromisoformat(expiration_str.replace("Z", "+00:00"))
                expirations[profile_name] = exp
            except (ValueError, TypeError):
                pass
        conn.close()
    except sqlite3.Error:
        pass

    return expirations


# --- Status computation ---

def compute_status(expiration: datetime | None, now: datetime) -> tuple[str, str, str]:
    """
    Compute status, expiration display, and time remaining for a profile.
    Returns (status, expires_at, time_remaining).
    """
    if expiration is None:
        return ("UNKNOWN", "N/A", "Unknown")

    if expiration > now:
        expires_at = expiration.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        remaining = expiration - now
        time_remaining = format_duration(remaining.total_seconds())
        return ("VALID", expires_at, time_remaining)
    else:
        expires_at = expiration.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        return ("EXPIRED", expires_at, "Expired")


def format_duration(total_seconds: float) -> str:
    """Format seconds into a human-readable duration."""
    seconds = int(total_seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m {secs:02d}s"
    return f"{secs:02d}s"


def status_sort_key(status: str) -> int:
    """Sort order: VALID first, UNKNOWN second, EXPIRED last."""
    if status == "VALID":
        return 0
    if status == "UNKNOWN":
        return 1
    return 2


# --- Display ---

def print_status_table(rows: list[tuple[str, str, str, str]], c, filter_text: str | None = None):
    """Print the credential status table with colors."""
    if filter_text:
        filter_lower = filter_text.lower()
        rows = [r for r in rows if filter_lower in r[0].lower()]

    if not rows:
        print(f"{c.DIM}No profiles found.{c.RESET}")
        return

    headers = ("Profile", "Status", "Expires At", "Time Remaining")
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    header_line = "  ".join(f"{h:<{widths[i]}}" for i, h in enumerate(headers))
    print(f"{c.BOLD}{header_line}{c.RESET}")
    print(f"{c.DIM}{'─' * (sum(widths) + 6)}{c.RESET}")

    for profile, status, expires_at, time_remaining in rows:
        if status == "VALID":
            status_colored = f"{c.GREEN}{status:<{widths[1]}}{c.RESET}"
        elif status == "EXPIRED":
            status_colored = f"{c.RED}{status:<{widths[1]}}{c.RESET}"
        else:
            status_colored = f"{c.YELLOW}{status:<{widths[1]}}{c.RESET}"

        if time_remaining == "Expired":
            time_colored = f"{c.RED}{time_remaining:<{widths[3]}}{c.RESET}"
        elif time_remaining == "Unknown":
            time_colored = f"{c.YELLOW}{time_remaining:<{widths[3]}}{c.RESET}"
        else:
            time_colored = f"{c.GREEN}{time_remaining:<{widths[3]}}{c.RESET}"

        profile_col = f"{profile:<{widths[0]}}"
        expires_col = f"{expires_at:<{widths[2]}}"
        print(f"{profile_col}  {status_colored}  {expires_col}  {time_colored}")


def print_summary(rows: list[tuple[str, str, str, str]], c):
    """Print a summary line below the table."""
    valid = sum(1 for r in rows if r[1] == "VALID")
    expired = sum(1 for r in rows if r[1] == "EXPIRED")
    unknown = sum(1 for r in rows if r[1] == "UNKNOWN")
    total = len(rows)

    parts = [f"{total} profiles"]
    if valid:
        parts.append(f"{c.GREEN}{valid} valid{c.RESET}")
    if expired:
        parts.append(f"{c.RED}{expired} expired{c.RESET}")
    if unknown:
        parts.append(f"{c.YELLOW}{unknown} unknown{c.RESET}")

    print(f"\n{' | '.join(parts)}")


# --- Status command ---

def cmd_status(args):
    """Show credential status for all profiles."""
    if args.no_color or not supports_color():
        c = NoColor
    else:
        c = Color

    aws_dir = get_aws_dir()

    samlsts_profiles = load_samlsts_profiles(aws_dir)
    credential_profiles = load_credentials_profiles(aws_dir)
    token_expirations = load_token_expirations(aws_dir)

    all_profiles = sorted(
        set(samlsts_profiles) | credential_profiles | set(token_expirations.keys()),
        key=str.lower,
    )

    if not all_profiles:
        print(f"{c.YELLOW}No AWS SAML profiles found.{c.RESET}")
        print(f"{c.DIM}Expected config at: {aws_dir / 'samlsts'}{c.RESET}")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    rows: list[tuple[str, str, str, str]] = []

    for profile in all_profiles:
        expiration = token_expirations.get(profile)
        status, expires_at, time_remaining = compute_status(expiration, now)
        rows.append((profile, status, expires_at, time_remaining))

    rows.sort(key=lambda r: (status_sort_key(r[1]), r[0].lower()))

    # Single profile mode
    if hasattr(args, "profile") and args.profile:
        rows = [r for r in rows if r[0] == args.profile]
        if not rows:
            print(f"{c.RED}Profile '{args.profile}' not found.{c.RESET}")
            sys.exit(1)

    print(f"\n{c.BOLD}{c.CYAN}AWS SAML Credential Status{c.RESET}")
    print(f"{c.DIM}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{c.RESET}\n")

    # Apply status filter (-v, -u, -x)
    if getattr(args, "valid", False):
        rows = [r for r in rows if r[1] == "VALID"]
    elif getattr(args, "unknown", False):
        rows = [r for r in rows if r[1] == "UNKNOWN"]
    elif getattr(args, "expired", False):
        rows = [r for r in rows if r[1] == "EXPIRED"]

    filter_text = getattr(args, "filter", None)
    print_status_table(rows, c, filter_text=filter_text)
    filtered_rows = rows if not filter_text else [r for r in rows if filter_text.lower() in r[0].lower()]
    print_summary(filtered_rows, c)
    print()


# --- Creds command ---

def cmd_creds(args):
    """Show encrypted credentials for already-authenticated profiles."""
    if args.no_color or not supports_color():
        c = NoColor
    else:
        c = Color

    aws_dir = get_aws_dir()

    # Read credentials file
    creds_path = aws_dir / "credentials"
    if not creds_path.exists():
        print(f"{c.RED}No credentials file found at {creds_path}{c.RESET}")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(str(creds_path))

    available_cred_profiles = set(config.sections())

    # Determine which profiles to show creds for
    profiles_to_show = []

    if hasattr(args, "filter") and args.filter:
        filter_lower = args.filter.lower()
        profiles_to_show = [p for p in sorted(available_cred_profiles) if filter_lower in p.lower()]
    elif hasattr(args, "profiles") and args.profiles:
        profiles_to_show = args.profiles
    elif hasattr(args, "profile") and args.profile:
        profiles_to_show = [args.profile]
    else:
        # Called via top-level -c flag — use top-level filter/status flags
        top_filter = getattr(args, "filter", None)
        top_profile = getattr(args, "profile", None)

        if top_profile:
            profiles_to_show = [top_profile]
        elif top_filter:
            filter_lower = top_filter.lower()
            profiles_to_show = [p for p in sorted(available_cred_profiles) if filter_lower in p.lower()]
        else:
            profiles_to_show = sorted(available_cred_profiles)

        # Apply status filter if -v/-x/-u used with -c
        if getattr(args, "valid", False) or getattr(args, "expired", False) or getattr(args, "unknown", False):
            token_expirations = load_token_expirations(aws_dir)
            now = datetime.now(timezone.utc)
            filtered = []
            for p in profiles_to_show:
                exp = token_expirations.get(p)
                if getattr(args, "valid", False):
                    if exp and exp > now:
                        filtered.append(p)
                elif getattr(args, "expired", False):
                    if exp and exp <= now:
                        filtered.append(p)
                elif getattr(args, "unknown", False):
                    if exp is None:
                        filtered.append(p)
            profiles_to_show = filtered

    if not profiles_to_show:
        print(f"{c.RED}No matching profiles with credentials found.{c.RESET}")
        sys.exit(1)

    # Validate profiles have credentials
    missing = [p for p in profiles_to_show if p not in available_cred_profiles]
    if missing:
        print(f"{c.RED}No credentials found for: {', '.join(missing)}{c.RESET}")
        # Continue with the ones that do exist
        profiles_to_show = [p for p in profiles_to_show if p in available_cred_profiles]
        if not profiles_to_show:
            sys.exit(1)

    # Import encryption utility
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    try:
        import Utilities
    except ImportError:
        print(f"{c.RED}Cannot import Utilities module for encryption{c.RESET}")
        sys.exit(1)

    # Show encrypted creds for each profile
    token_expirations = load_token_expirations(aws_dir)
    now = datetime.now(timezone.utc)

    for profile in profiles_to_show:
        access_key = config.get(profile, "aws_access_key_id", fallback=None)
        secret_key = config.get(profile, "aws_secret_access_key", fallback=None)
        session_token = config.get(profile, "aws_session_token", fallback=None)

        if not all([access_key, secret_key, session_token]):
            print(f"{c.YELLOW}⊘ {profile} — incomplete credentials, skipping{c.RESET}")
            continue

        # Check expiration
        expiration = token_expirations.get(profile)
        if expiration and expiration < now:
            status_note = f" {c.YELLOW}(expired){c.RESET}"
        elif expiration:
            remaining = format_duration((expiration - now).total_seconds())
            status_note = f" {c.GREEN}({remaining} remaining){c.RESET}"
        else:
            status_note = f" {c.DIM}(unknown expiry){c.RESET}"

        encrypted = Utilities.encrypt_credentials(access_key, secret_key, session_token)
        if encrypted == "Encryption Error":
            print(f"{c.RED}✗ {profile} — encryption failed (check ~/.aws/public_key.pem){c.RESET}")
            continue

        print(f"\n{c.BOLD}{profile}{c.RESET}{status_note}")
        print(encrypted)

    print()


# --- Auth command ---

def save_token_expiration(aws_dir: Path, profile: str, duration_seconds: int):
    """Write token expiration to the SQLite DB after successful auth."""
    db_path = aws_dir / "aws_saml.db"
    expiration = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
    now_str = datetime.now().isoformat()

    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS token_state "
            "(profile_name TEXT PRIMARY KEY, expiration TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT OR REPLACE INTO token_state (profile_name, expiration, created_at) VALUES (?, ?, ?)",
            (profile, expiration.isoformat(), now_str),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass


def get_session_duration(aws_dir: Path, profile: str) -> int:
    """Read session duration from samlsts config (profile or global), default 14400."""
    config_path = aws_dir / "samlsts"
    if not config_path.exists():
        return 14400

    config = configparser.ConfigParser()
    config.read(str(config_path))

    # Check profile section
    if config.has_section(profile) and config.has_option(profile, "sessionduration"):
        try:
            return int(config.get(profile, "sessionduration"))
        except ValueError:
            pass

    # Check global section
    if config.has_section("global") and config.has_option("global", "sessionduration"):
        try:
            return int(config.get("global", "sessionduration"))
        except ValueError:
            pass

    return 14400


def cmd_auth(args):
    """Authenticate a profile using the existing getCredentials.py flow."""
    if args.no_color or not supports_color():
        c = NoColor
    else:
        c = Color

    aws_dir = get_aws_dir()
    samlsts_profiles = load_samlsts_profiles(aws_dir)

    # Determine which profiles to auth
    profiles_to_auth = []

    if args.filter:
        # Auth all profiles matching the filter
        filter_lower = args.filter.lower()
        profiles_to_auth = [p for p in samlsts_profiles if filter_lower in p.lower()]
        if not profiles_to_auth:
            print(f"{c.RED}No profiles match filter '{args.filter}'{c.RESET}")
            sys.exit(1)
    elif args.profiles:
        # Auth a list of profiles
        profiles_to_auth = args.profiles
    elif args.profile:
        # Single profile (positional)
        profiles_to_auth = [args.profile]
    else:
        print(f"{c.RED}Provide a profile name, -p <profiles>, or -f <filter>{c.RESET}")
        sys.exit(1)

    # Validate all profiles exist
    invalid = [p for p in profiles_to_auth if p not in samlsts_profiles]
    if invalid:
        print(f"{c.RED}Profile(s) not found: {', '.join(invalid)}{c.RESET}")
        print(f"{c.DIM}Available profiles:{c.RESET}")
        for p in samlsts_profiles:
            print(f"  {p}")
        sys.exit(1)

    # Use batch auth (shared SAML login) when multiple profiles are requested
    if len(profiles_to_auth) > 1:
        _batch_auth(profiles_to_auth, args, aws_dir, c)
    else:
        _single_auth(profiles_to_auth[0], args, aws_dir, c)


def _batch_auth(profiles: list[str], args, aws_dir: Path, c):
    """Authenticate multiple profiles with shared SAML login (one MFA prompt per identity group)."""
    # Import batch_auth from the same directory
    script_dir = Path(__file__).resolve().parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    from batch_auth import perform_batch_auth

    print(f"{c.BOLD}{c.CYAN}Batch authenticating {len(profiles)} profile(s) (shared login per identity group){c.RESET}\n")

    def status_cb(event, profile, message):
        if event == "INFO":
            print(f"{c.DIM}{message}{c.RESET}")
        elif event == "LOGIN":
            print(f"\n{c.BOLD}{c.CYAN}{message}{c.RESET}\n")
        elif event == "OK":
            duration = get_session_duration(aws_dir, profile)
            save_token_expiration(aws_dir, profile, duration)
            print(f"  {c.GREEN}✓ {profile}{c.RESET} — {message}")
        elif event == "FAIL":
            print(f"  {c.RED}✗ {profile}{c.RESET} — {message}")
        elif event == "SKIP":
            print(f"  {c.YELLOW}⊘ {profile}{c.RESET} — {message}")

    try:
        results = perform_batch_auth(
            profiles=profiles,
            use_fastpass=args.fastpass,
            use_debug=args.debug,
            show_encrypted=args.encrypted,
            status_callback=status_cb,
        )

        # Summary
        succeeded = sum(1 for v in results.values() if v)
        failed = sum(1 for v in results.values() if not v)
        print(f"\n{c.BOLD}Batch complete:{c.RESET} {c.GREEN}{succeeded} succeeded{c.RESET}", end="")
        if failed:
            print(f", {c.RED}{failed} failed{c.RESET}")
        else:
            print()
        print()

    except KeyboardInterrupt:
        print(f"\n{c.YELLOW}Cancelled.{c.RESET}")
        sys.exit(130)


def _single_auth(profile: str, args, aws_dir: Path, c):
    """Authenticate a single profile via subprocess (preserves interactive password prompt)."""
    script_dir = Path(__file__).resolve().parent
    get_creds = script_dir / "getCredentials.py"

    if not get_creds.exists():
        print(f"{c.RED}Cannot find getCredentials.py at: {get_creds}{c.RESET}")
        sys.exit(1)

    cmd = [sys.executable, str(get_creds), "--profilename", profile]

    if args.fastpass:
        cmd.append("--fastpass")
    if args.stored_password and not args.no_stored_password:
        cmd.append("--storedpw")
    if args.debug:
        cmd.append("--debug")
    if args.browser:
        cmd.extend(["--browser", args.browser])
    if args.encrypted:
        cmd.append("--encrypted")

    print(f"{c.BOLD}{c.CYAN}Authenticating profile: {profile}{c.RESET}\n")

    try:
        result = subprocess.run(cmd, cwd=str(script_dir))
        if result.returncode == 0:
            duration = get_session_duration(aws_dir, profile)
            save_token_expiration(aws_dir, profile, duration)
            print(f"\n{c.GREEN}✓ Authentication successful for: {profile}{c.RESET}\n")
        else:
            print(f"\n{c.RED}✗ Authentication failed for: {profile} (exit code: {result.returncode}){c.RESET}\n")
    except KeyboardInterrupt:
        print(f"\n{c.YELLOW}Cancelled.{c.RESET}")
        sys.exit(130)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        prog="samlstat",
        description="AWS SAML credential status and authentication CLI.",
        epilog="""examples:
  samlstat                        show all profiles
  samlstat -f natl                filter by name
  samlstat -v                     show only valid
  samlstat -xf natl               expired natl profiles
  samlstat -cf natl               encrypted creds for natl profiles
  samlstat -cvf tier1             encrypted creds for valid tier1 profiles
  samlstat auth <profile>         authenticate a profile
  samlstat auth -f tier1          authenticate all tier1 profiles
  samlstat auth -p prof1 prof2    authenticate multiple profiles
  samlstat creds <profile>        show encrypted creds for a single profile
  samlstat creds -f tier1         show encrypted creds for all tier1 profiles""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable color output",
    )
    # Top-level filter/profile flags so 'samlstat -f prod' works without 'status' subcommand
    parser.add_argument(
        "-f", "--filter",
        help="Filter profiles by name (case-insensitive substring match)",
    )
    parser.add_argument(
        "-v", "--valid",
        action="store_true",
        help="Show only VALID profiles",
    )
    parser.add_argument(
        "-u", "--unknown",
        action="store_true",
        help="Show only UNKNOWN profiles",
    )
    parser.add_argument(
        "-x", "--expired",
        action="store_true",
        help="Show only EXPIRED profiles",
    )
    parser.add_argument(
        "-p", "--profile",
        help="Show status for a single profile only",
    )
    parser.add_argument(
        "-c", "--creds",
        action="store_true",
        help="Show encrypted credentials for matching profiles",
    )

    subparsers = parser.add_subparsers(dest="command")

    # --- status ---
    status_parser = subparsers.add_parser(
        "status",
        aliases=["s"],
        help="Show credential status for all profiles (default)",
    )
    status_parser.add_argument(
        "-f", "--filter",
        help="Filter profiles by name (case-insensitive substring match)",
    )
    status_parser.add_argument(
        "-v", "--valid",
        action="store_true",
        help="Show only VALID profiles",
    )
    status_parser.add_argument(
        "-u", "--unknown",
        action="store_true",
        help="Show only UNKNOWN profiles",
    )
    status_parser.add_argument(
        "-x", "--expired",
        action="store_true",
        help="Show only EXPIRED profiles",
    )
    status_parser.add_argument(
        "-p", "--profile",
        help="Show status for a single profile only",
    )

    # --- auth ---
    auth_parser = subparsers.add_parser(
        "auth",
        aliases=["a"],
        help="Authenticate and get credentials for a profile",
        description="Authenticate one or more AWS SAML profiles.",
        epilog="""examples:
  samlstat auth natldev-tier1                     single profile
  samlstat auth -p natldev-tier1 natlprod-tier1   multiple profiles
  samlstat auth -f tier1                          all profiles matching filter
  samlstat auth -f prod --encrypted               with encrypted output""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    auth_parser.add_argument(
        "profile",
        nargs="?",
        help="Profile name to authenticate (single profile)",
    )
    auth_parser.add_argument(
        "-p", "--profiles",
        nargs="+",
        help="Space-separated list of profiles to authenticate",
    )
    auth_parser.add_argument(
        "-f", "--filter",
        help="Authenticate all profiles matching this filter (case-insensitive substring)",
    )
    auth_parser.add_argument(
        "--fastpass", "-fp",
        action="store_true",
        help="Use Okta FastPass (biometric/device auth, no password)",
    )
    auth_parser.add_argument(
        "--stored-password", "-sp",
        action="store_true",
        default=True,
        help="Use stored password (default: enabled)",
    )
    auth_parser.add_argument(
        "--no-stored-password",
        action="store_true",
        help="Prompt for password instead of using stored",
    )
    auth_parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Show browser window during login",
    )
    auth_parser.add_argument(
        "--browser", "-b",
        help="Browser to use (chrome, firefox)",
    )
    auth_parser.add_argument(
        "--encrypted", "-e",
        action="store_true",
        help="Display encrypted credentials after auth",
    )

    # --- creds ---
    creds_parser = subparsers.add_parser(
        "creds",
        aliases=["c"],
        help="Show encrypted credentials for an already-authenticated profile",
        description="Display encrypted credentials from ~/.aws/credentials without re-authenticating.",
        epilog="""examples:
  samlstat creds natlprod-admin                   single profile
  samlstat creds -p natldev-tier1 natlqa-tier1    multiple profiles
  samlstat creds -f tier1                         all profiles matching filter
  samlstat -cf natl                               shorthand via top-level flag
  samlstat -cvf tier1                             only valid tier1 profiles""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    creds_parser.add_argument(
        "profile",
        nargs="?",
        help="Profile name to show encrypted credentials for",
    )
    creds_parser.add_argument(
        "-p", "--profiles",
        nargs="+",
        help="Space-separated list of profiles",
    )
    creds_parser.add_argument(
        "-f", "--filter",
        help="Show encrypted creds for all profiles matching this filter",
    )

    args = parser.parse_args()

    if args.command in ("auth", "a"):
        cmd_auth(args)
    elif args.command in ("creds", "c"):
        cmd_creds(args)
    elif getattr(args, "creds", False):
        # Top-level -c flag
        cmd_creds(args)
    else:
        # Default to status (handles None, "status", "s")
        cmd_status(args)


if __name__ == "__main__":
    main()

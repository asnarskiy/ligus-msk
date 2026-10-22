"""Build a self-contained PHP-hosting release; never copy local credentials."""
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from legal import consent_document
SITE = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
p = argparse.ArgumentParser()
p.add_argument('--site-url', default='https://ligus-msk.ru')
p.add_argument('--layout', choices=['standard', 'regru'], default='standard')
a = p.parse_args()
u = urlsplit(a.site_url)
if u.scheme != 'https' or not u.hostname or u.path not in ('', '/') or u.query or u.fragment or u.username:
    p.error('--site-url must be an HTTPS origin without a path')
release = ROOT / 'release' / ('ligus-regru' if a.layout == 'regru' else 'ligus-hosting')
if release.exists():
    if not release.resolve().is_relative_to((ROOT / 'release').resolve()):
        raise ValueError('Release directory is outside the workspace release folder')
    shutil.rmtree(release)
public = release / 'www' / u.hostname if a.layout == 'regru' else release / 'public_html'
private = release / 'private' / 'contact'
env = dict(os.environ, OUTPUT_DIR=str(public), FORM_PROVIDER='smtp', BASE_PATH='', SITE_URL=a.site_url.rstrip('/'),
           CONTACT_FORM_ENABLED='1' if SITE.get('contactFormEnabled') else '0')
subprocess.run([sys.executable, str(ROOT / 'build.py')], env=env, check=True)
shutil.copytree(ROOT / 'server' / 'public', public, dirs_exist_ok=True)
if a.layout == 'regru':
    entry = public / 'api' / 'contact.php'
    entry.write_text(entry.read_text().replace('dirname(__DIR__, 2)', 'dirname(__DIR__, 3)'))
private.mkdir(parents=True)
(private / 'consent.json').write_text(json.dumps(consent_document(SITE), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
# Explicit allowlist prevents config.php / runtime / backups entering the release.
for name in ['config.example.php', 'handler.php', 'check.php', 'maintenance.php']:
    shutil.copy2(ROOT / 'server' / 'private' / 'contact' / name, private / name)
shutil.copytree(ROOT / 'server' / 'private' / 'contact' / 'vendor', private / 'vendor')
instructions = (ROOT / 'docs' / 'smtp-hosting.md').read_text(encoding='utf-8')
instructions = instructions.replace('[deployment.md](deployment.md)', '`docs/deployment.md` в репозитории')
instructions = instructions.replace('[инструкции публикации](agents/release.md)', '`docs/agents/release.md` в репозитории')
if not SITE.get('legalDetailsConfirmed'):
    instructions = '# Проект для проверки — не публиковать\n\nЮридические сведения и условия обработки ещё не подтверждены владельцем. См. [перечень необходимых действий](personal-data.md).\n\n' + instructions
(release / 'README.md').write_text(instructions, encoding='utf-8')
shutil.copy2(ROOT / 'docs' / 'personal-data.md', release / 'personal-data.md')
subprocess.run([sys.executable, str(ROOT / 'verify.py')], env=env, check=True)
for page in public.rglob('*.html'):
    text = page.read_text()
    assert 'formsubmit.co' not in text and 'forms.yandex.ru' not in text, page
    if 'request-form' in text:
        assert 'data-provider="smtp"' in text and 'action="/api/contact.php"' in text, page
assert not (private / 'config.php').exists()
assert not (public / 'private').exists()
archive = shutil.make_archive(str(release), 'zip', release.parent, release.name)
print(f'Hosting package: {archive}\nDocument root: {public}\nContact form enabled in release: {bool(SITE.get("contactFormEnabled"))}. Private config.php is also required.')
if not SITE.get('legalDetailsConfirmed'):
    print('REVIEW ONLY: company address, returns, working hours and data retention await owner confirmation. Do not publish this package yet.')

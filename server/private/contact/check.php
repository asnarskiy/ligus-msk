<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
require __DIR__ . '/handler.php';
umask(0077);
try {
    $c = \Ligus\Contact\configuration();
    $consent = \Ligus\Contact\consentDocument();
    \Ligus\Contact\database($c);
    echo "OK: configuration, consent snapshot, PHP extensions and private storage. SMTP delivery not tested.\n";
    echo "Website form: " . (($consent['form_enabled'] ?? false) === true ? 'enabled' : 'disabled') . ".\n";
} catch (Throwable $e) {
    fwrite(STDERR, "NOT READY: " . $e->getMessage() . "\n");
    exit(1);
}

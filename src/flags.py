"""Check that Meta's app still declares the MobileConfig settings our overrides change."""
import json

from upstream import APP_NAME, ROOT

# params_map.txt type column; overrides use MobileConfig's own type names.
TYPES = {'': 'boolean', '8': 'int64', 'c': 'string'}
USB_KEYS = {'oculus_remote_desktop:usb_transport_enabled', 'remote_desktop_mqrd_default:mqrd_enable_disco_server'}
USB_CODE = (b'TransportUsbServer', b'highwind.usb.server', b'highwind.transport.async_usb_server')


def overrides():
    """The MobileConfig values the patched app loads."""
    values = json.loads((ROOT / 'src/overrides.json').read_text())
    # These existing Meta switches disable both silent-update implementations.
    for key in ('frl_mqrd_silent_update_enabled', 'frl_mqrd_silent_update_phase_2'):
        values['remote_desktop_mqrd_default:' + key] = {'type': 'boolean', 'value': 'false'}
    return values


def declared(params_map):
    """Map 'config:param' to its type from Contents/Resources/params_map.txt."""
    params, config = {}, None
    for line in params_map.splitlines()[1:]:
        fields = line.split(',')
        if line.startswith('*'):
            config = fields[0][1:]
        elif config and fields[0]:
            params[f'{config}:{fields[0]}'] = TYPES.get(fields[2] if len(fields) > 2 else '', 'other')
    return params


def findings(params, executable, values):
    """Overrides that no longer change anything. Server-side rollouts are not visible here."""
    usb_code = any(marker in executable for marker in USB_CODE)
    notes = []
    for key, override in values.items():
        # Some settings are read by full name in code rather than listed in params_map.txt.
        missing = key not in params and b'\0' + key.encode() + b'\0' not in executable
        if missing and key in USB_KEYS and usb_code:
            notes.append(f'Meta no longer gates {key} and still ships its USB code: USB is likely on for '
                         'everyone, so the USB override is no longer needed. The 120 FPS patches still apply.')
        elif missing and key in USB_KEYS:
            notes.append(f'Meta removed {key} along with its USB code; USB transport is likely gone.')
        elif missing:
            notes.append(f'Meta no longer declares {key}; its override has no effect.')
        elif key in params and params[key] != override['type']:
            notes.append(f"Meta now declares {key} as {params[key]}, not {override['type']}; its override may be ignored.")
    return notes


def stale_overrides(app):
    params = declared((app / 'Contents/Resources/params_map.txt').read_text())
    return findings(params, (app / 'Contents/MacOS' / APP_NAME).read_bytes(), overrides())

#include <mach-o/dyld.h>
#include <crt_externs.h>
#include <CoreFoundation/CoreFoundation.h>
#include <libproc.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// Held until process exit. No daemon, adb server, or wrapper process is needed.
static int host_lock = -1;

__attribute__((constructor))
static void configure_usb(void) {
    char executable[PATH_MAX], resolved[PATH_MAX], config[PATH_MAX];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) || !realpath(executable, resolved)) _exit(78);
    char *slash = strrchr(resolved, '/');
    if (!slash) _exit(78);
    *slash = '\0';
    int n = snprintf(config, sizeof(config), "%s/../Resources/usb-overrides.json", resolved);
    if (n < 0 || (size_t)n >= sizeof(config) || access(config, R_OK)) {
        fprintf(stderr, "Quest VD USB: bundled configuration is missing.\n");
        _exit(78);
    }
    if (setenv("MQRD_MC_OVERRIDES_FILE", config, 1)) _exit(78);
    for (int i = 1; i < *_NSGetArgc(); i++) {
        if (!strcmp((*_NSGetArgv())[i], "--usb-config-check")) {
            printf("Quest VD USB configuration: %s\n", config);
            fflush(stdout);
            _exit(0); // Smoke check never starts the host or asks for permissions.
        }
    }
    char temp[PATH_MAX], lock[PATH_MAX];
    size_t needed = confstr(_CS_DARWIN_USER_TEMP_DIR, temp, sizeof(temp));
    if (!needed || needed > sizeof(temp)) _exit(78);
    n = snprintf(lock, sizeof(lock), "%squest-vd-mac-usb.lock", temp);
    if (n < 0 || (size_t)n >= sizeof(lock)) _exit(78);
    host_lock = open(lock, O_CREAT | O_RDWR | O_NOFOLLOW | O_CLOEXEC, 0600);
    struct stat st;
    if (host_lock < 0 || fstat(host_lock, &st) || !S_ISREG(st.st_mode) || st.st_uid != getuid()) _exit(78);
    if (flock(host_lock, LOCK_EX | LOCK_NB)) {
        fprintf(stderr, "Quest VD USB: another patched host is running.\n");
        _exit(2);
    }
    int capacity = proc_listallpids(NULL, 0) + 128;
    if (capacity < 128) _exit(78);
    pid_t *pids = calloc((size_t)capacity, sizeof(pid_t));
    if (!pids) _exit(78);
    int count = proc_listallpids(pids, capacity * sizeof(pid_t));
    const char *suffix = "/Contents/MacOS/Meta Quest Virtual Display";
    for (int i = 0; i < count && i < capacity; i++) {
        if (pids[i] == getpid()) continue;
        struct proc_bsdinfo info;
        if (proc_pidinfo(pids[i], PROC_PIDTBSDINFO, 0, &info, sizeof(info)) != sizeof(info) || info.pbi_uid != getuid()) continue;
        char path[PROC_PIDPATHINFO_MAXSIZE];
        if (proc_pidpath(pids[i], path, sizeof(path)) <= 0) continue;
        size_t length = strlen(path), suffix_length = strlen(suffix);
        if (length >= suffix_length && !strcmp(path + length - suffix_length, suffix)) {
            fprintf(stderr, "Quest VD USB: quit the other Meta desktop host first (PID %d).\n", pids[i]);
            free(pids);
            _exit(2); // Never leave a second host waiting on a blocking dialog.
        }
    }
    free(pids);
    CFPreferencesSetAppValue(CFSTR("SUEnableAutomaticChecks"), kCFBooleanFalse, kCFPreferencesCurrentApplication);
    CFPreferencesSetAppValue(CFSTR("SUAutomaticallyUpdate"), kCFBooleanFalse, kCFPreferencesCurrentApplication);
    CFPreferencesAppSynchronize(kCFPreferencesCurrentApplication);
}

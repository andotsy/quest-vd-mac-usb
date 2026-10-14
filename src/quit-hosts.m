#import <AppKit/AppKit.h>

static int validate(NSString *path, NSString *version) {
    if (![NSFileManager.defaultManager fileExistsAtPath:path]) return 0;
    NSDictionary *info = [NSDictionary dictionaryWithContentsOfFile:
        [path stringByAppendingPathComponent:@"Contents/Info.plist"]];
    NSArray *ids = @[@"com.meta.virtualdesktop", @"com.codex.metausb120test", @"io.github.quest-vd-mac-usb"];
    if (!info || ![ids containsObject:info[@"CFBundleIdentifier"]]) {
        fprintf(stderr, "A different app occupies the destination. Nothing replaced.\n");
        return 1;
    }
    NSString *current = info[@"CFBundleVersion"];
    NSRegularExpression *pattern = [NSRegularExpression regularExpressionWithPattern:
        @"^[0-9]+(\\.[0-9]+){1,5}$" options:0 error:NULL];
    if (![current isKindOfClass:NSString.class] ||
        [pattern numberOfMatchesInString:current options:0 range:NSMakeRange(0, current.length)] != 1 ||
        [current compare:version options:NSNumericSearch] == NSOrderedDescending) {
        fprintf(stderr, "The installed version is newer or unrecognized. Nothing replaced.\n");
        return 1;
    }
    return 0;
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc == 4 && !strcmp(argv[1], "--validate"))
            return validate([NSString stringWithUTF8String:argv[2]], [NSString stringWithUTF8String:argv[3]]);
        if (argc != 2 || strcmp(argv[1], "--quit")) return 64;
        NSMutableArray<NSRunningApplication *> *hosts = [NSMutableArray array];
        for (NSRunningApplication *app in NSWorkspace.sharedWorkspace.runningApplications) {
            if ([app.executableURL.path hasSuffix:@"/Contents/MacOS/Meta Quest Virtual Display"]) {
                [hosts addObject:app];
                [app terminate];
            }
        }
        NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:15];
        while ([deadline timeIntervalSinceNow] > 0) {
            BOOL allExited = YES;
            for (NSRunningApplication *app in hosts) if (!app.terminated) allExited = NO;
            if (allExited) return 0;
            [NSRunLoop.currentRunLoop runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
        }
        fprintf(stderr, "Quit Meta Quest Virtual Display, then run the installer again.\n");
        return 1;
    }
}

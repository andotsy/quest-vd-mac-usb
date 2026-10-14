#import <AppKit/AppKit.h>

int main(void) {
    @autoreleasepool {
        NSMutableArray<NSRunningApplication *> *hosts = [NSMutableArray array];
        for (NSRunningApplication *app in NSWorkspace.sharedWorkspace.runningApplications) {
            if ([app.executableURL.path hasSuffix:@"/Contents/MacOS/Meta Quest Virtual Display"]) {
                [hosts addObject:app];
                fprintf(stderr, "Requesting normal quit of Meta desktop host %d\n", app.processIdentifier);
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
        fprintf(stderr, "A host did not quit. Quit it manually and run the installer again. Nothing was replaced.\n");
        return 1;
    }
}

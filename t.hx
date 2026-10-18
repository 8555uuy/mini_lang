d = {a:1, b:2};
print(d, keys(d), has(d,"a"), len(d));
d.c = 3;
set(d,"e",5);
print(items(d));
del d.a;
print(d);
for (k in d) { print("key:", k); }
for (x in [10,20,30]) { if (x == 20) { continue; } print("x:", x); }
i = 0;
while (true) { i += 1; if (i > 3) { break; } }
print("i =", i, "i>3 =", i > 3);
print(upper("abc"), trim("  hi  "), join("-", ["a","b"]), max([3,9,2]));
z = d;
print("dar(z) =", dar(z));

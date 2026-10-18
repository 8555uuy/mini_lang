# HX 语言示例：print(...) 直接输出
fn fib(n) {
  if (n < 2) { return n; }
  return fib(n - 1) + fib(n - 2);
}
fn add(a, b) { return a + b; }

print("fib(10) =", fib(10));
print("add(3,4) =", add(3, 4));

n = 42;
print("dar(n) =", dar(n), "| n =", n);
s = "hi";
print("dar(s) =", dar(s));
arr2 = [1, 2];
print("dar(arr2) =", dar(arr2));
print "无括号 print 也行";

arr = [1, 2, 3];
push(arr, 4);
print("arr =", arr, "len =", len(arr));

d = {name: "hx", ver: 3};
print("dict =", d, "name =", d.name, "ver =", d["ver"]);

i = 0;
sum = 0;
while (i < len(arr)) { sum = sum + arr[i]; i = i + 1; }
print("sum =", sum);

for (k in d) { print("key:", k); }
for (j = 0; j < 3; j += 1) { print("j =", j); }
print(upper("abc"), max([3,9,2]));

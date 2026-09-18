num = int(input())
last_digit = None
next_digit = None
flag = True
while num != 0:
    last_digit = num % 10
    if last_digit != next_digit and next_digit != None:
        flag = False
    next_digit = last_digit
    num //= 10

if flag == True:
    print('YES')
else:
    print('NO')
from reserve import main

if __name__ == '__main__':
    main()


# Aliyun FC
def handler(event, context):
    main()
    return


# Tencent SCF
def main_handler(event, context):
    main()
    return


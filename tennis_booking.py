#!/usr/bin/env python3
"""
网球场快速预订脚本
在已登录的预订页面上快速选择时间段并点击预订按钮
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
try:
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
import time
from datetime import datetime


def setup_driver(use_existing_browser=True):
    """
    设置 Edge WebDriver
    
    Args:
        use_existing_browser: 是否使用已打开的浏览器（True）或打开新浏览器（False）
    """
    edge_options = Options()
    
    if use_existing_browser:
        # 连接到已存在的 Edge 浏览器
        # 使用远程调试端口连接到已打开的浏览器
        edge_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
        print("正在连接到已打开的 Edge 浏览器...")
        
        try:
            # 不需要启动新的浏览器，直接连接
            if WEBDRIVER_MANAGER_AVAILABLE:
                try:
                    service = Service(EdgeChromiumDriverManager().install())
                    driver = webdriver.Edge(service=service, options=edge_options)
                except:
                    driver = webdriver.Edge(options=edge_options)
            else:
                driver = webdriver.Edge(options=edge_options)
            
            print("✅ 已连接到现有浏览器")
            return driver
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            print("\n请先启动 Edge（远程调试模式）：")
            print('   "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge" --remote-debugging-port=9222')
            print("或运行: ./start_edge.sh")
            raise
    else:
        # 打开新的浏览器窗口
        edge_options.add_argument('--disable-blink-features=AutomationControlled')
        
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                service = Service(EdgeChromiumDriverManager().install())
                driver = webdriver.Edge(service=service, options=edge_options)
            except:
                driver = webdriver.Edge(options=edge_options)
        else:
            driver = webdriver.Edge(options=edge_options)
        
        driver.maximize_window()
        return driver


def click_refresh_button(driver):
    """
    点击刷新按钮重新加载当天视图
    按钮格式: <i class="..." onclick="refreshDayView()"></i>
    """
    try:
        # 使用最精确的选择器
        selectors = [
            "i[onclick='refreshDayView()']",
            "//i[contains(@onclick, 'refreshDayView')]",
            "i.icon-repeat[onclick='refreshDayView()']",
        ]
        
        for selector in selectors:
            try:
                if selector.startswith("//"):
                    button = driver.find_element(By.XPATH, selector)
                else:
                    button = driver.find_element(By.CSS_SELECTOR, selector)
                
                if button.is_displayed():
                    driver.execute_script("arguments[0].click();", button)
                    print("🔄 已点击刷新按钮，等待页面更新...")
                    time.sleep(2)  # 等待页面刷新
                    return True
            except:
                continue
        
        print("⚠️ 未找到刷新按钮")
        return False
    except Exception as e:
        print(f"刷新按钮点击失败: {e}")
        return False


def find_available_slots(driver, time_range_start=14, time_range_end=21, court_numbers=[6, 7, 8, 9, 10]):
    """
    查找所有可用的时间段和球场组合
    按钮格式: <button data-value="800|900|10" class="available" onclick="toggleCourt(this)">10</button>
    data-value格式: 开始时间|结束时间|球场号 (时间为24小时制，如800表示8:00am)
    """
    # 格式化时间显示
    start_display = f"{time_range_start}:00" if time_range_start < 12 else f"{time_range_start-12}:00pm" if time_range_start > 12 else "12:00pm"
    end_display = f"{time_range_end}:00" if time_range_end < 12 else f"{time_range_end-12}:00pm" if time_range_end > 12 else "12:00pm"
    print(f"正在查找可用时间段（{start_display} - {end_display}，球场{court_numbers}）...")
    time.sleep(2)
    available_slots = []
    
    try:
        # 查找所有带data-value和available class的按钮
        buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-value].available[onclick='toggleCourt(this)']")
        
        for btn in buttons:
            try:
                if not btn.is_displayed():
                    continue
                
                classes = btn.get_attribute("class") or ""
                # 排除已选中的按钮
                if "selected" in classes:
                    continue
                
                # 解析data-value: "开始时间|结束时间|球场号"
                data_value = btn.get_attribute("data-value")
                if not data_value:
                    continue
                    
                parts = data_value.split("|")
                if len(parts) != 3:
                    continue
                
                start_time, end_time, court = parts
                court_num = int(court)
                
                # 过滤球场号
                if court_num not in court_numbers:
                    continue
                
                # 解析开始时间（例如：1400 -> 14点）
                start_hour = int(start_time[:2]) if len(start_time) >= 2 else int(start_time[0])
                
                # 检查时间范围
                if time_range_start <= start_hour < time_range_end:
                    # 格式化时间显示
                    time_display = f"{start_time}-{end_time} 球场{court}"
                    available_slots.append((btn, time_display, start_hour, court_num))
            except:
                continue
                
    except Exception as e:
        print(f"查找失败: {e}")
    
    # 按时间和球场排序
    available_slots.sort(key=lambda x: (x[2], x[3]))
    
    print(f"找到 {len(available_slots)} 个可用时间段和球场组合")
    if not available_slots:
        print("⚠️ 未找到可用时间段")
    
    return available_slots


def find_consecutive_slots(available_slots, num_consecutive=2, preferred_court=None):
    """
    查找连续的时间段（同一球场）
    
    Args:
        available_slots: 可用时间段列表 [(element, time_display, hour, court_num), ...]
        num_consecutive: 需要的连续时间段数量
        preferred_court: 优先选择的球场号
    
    Returns:
        连续时间段列表，如果找到；否则返回None
    """
    # 按球场分组
    by_court = {}
    for slot in available_slots:
        elem, time_display, hour, court_num = slot
        if court_num not in by_court:
            by_court[court_num] = []
        by_court[court_num].append(slot)
    
    # 优先检查指定球场
    courts_to_check = [preferred_court] if preferred_court and preferred_court in by_court else sorted(by_court.keys())
    
    # 在每个球场中查找连续时间段
    for court_num in courts_to_check:
        slots = by_court.get(court_num, [])
        slots.sort(key=lambda x: x[2])  # 按小时排序
        
        # 查找连续的时间段
        for i in range(len(slots) - num_consecutive + 1):
            consecutive = [slots[i]]
            for j in range(i + 1, len(slots)):
                if slots[j][2] == consecutive[-1][2] + 1:
                    consecutive.append(slots[j])
                    if len(consecutive) == num_consecutive:
                        return consecutive
                else:
                    break
    
    return None


def select_slots(driver, num_slots, time_range_start=14, time_range_end=21, alternative_start=None, alternative_end=None, court_numbers=None):
    """
    选择指定数量的时间段，优先选择连续的时间段（同一球场）
    分阶段选择策略：
    1. 优先从6,7,8,9,10号场在首选时间段选择2小时连续时间
    2. 如果不足，扩展到1,4,6,7,8,9,10号场在首选时间段
    3. 如果还不足，在备选时间段重复1-2步骤
    4. 最后降级为1小时
    
    每个按钮同时包含时间段和球场信息，点击即选中
    
    Args:
        time_range_start: 首选开始时间（24小时制）
        time_range_end: 首选结束时间（24小时制）
        alternative_start: 备选开始时间（24小时制）
        alternative_end: 备选结束时间（24小时制）
    
    Returns:
        (成功, 实际选择的数量, 选择详情列表)
        选择详情格式: [(时间显示, 球场号), ...]
    """
    preferred_courts = [6, 7, 8, 9, 10]
    extended_courts = [1, 4, 6, 7, 8, 9, 10]
    target_slots = None
    actual_num_slots = num_slots
    
    # 定义时间段列表（首选时间段优先）
    time_ranges = [(time_range_start, time_range_end, "首选时间段")]
    if alternative_start is not None and alternative_end is not None:
        time_ranges.append((alternative_start, alternative_end, "备选时间段"))
    
    # 遍历时间段
    for current_start, current_end, time_label in time_ranges:
        if target_slots:
            break  # 已找到合适的时间段
        
        print(f"\n🕐 尝试{time_label}: {current_start-12 if current_start > 12 else current_start}:00pm - {current_end-12 if current_end > 12 else current_end}:00pm")
        
        # 阶段1: 优先从6,7,8,9,10号场选择
        print("📍 阶段1: 在6,7,8,9,10号场中查找...")
        available_slots = find_available_slots(driver, time_range_start=current_start, time_range_end=current_end, court_numbers=preferred_courts)
    
        # 尝试找到连续时间段
        if num_slots >= 2 and available_slots:
            consecutive_slots = find_consecutive_slots(available_slots, num_slots)
            if consecutive_slots:
                court_num = consecutive_slots[0][3]
                print(f"✅ 在{time_label}的优先球场找到 {num_slots} 个连续时间段（球场{court_num}）")
                target_slots = consecutive_slots
                continue  # 找到了，跳出本次循环
        
        # 阶段2: 如果没找到，扩展到1,4号场
        if not target_slots:
            print("📍 阶段2: 扩展到1,4,6,7,8,9,10号场...")
            available_slots = find_available_slots(driver, time_range_start=current_start, time_range_end=current_end, court_numbers=extended_courts)
            
            if num_slots >= 2 and available_slots:
                consecutive_slots = find_consecutive_slots(available_slots, num_slots)
                if consecutive_slots:
                    court_num = consecutive_slots[0][3]
                    print(f"✅ 在{time_label}的扩展球场找到 {num_slots} 个连续时间段（球场{court_num}）")
                    target_slots = consecutive_slots
    
    # 阶段3: 所有时间段都试过了，如果还是没找到，降级为1个时间段
    if not target_slots:
        print("\n📍 阶段3: 降级为1个小时...")
        actual_num_slots = 1
        
        # 再次遍历所有时间段找1个小时
        for current_start, current_end, time_label in time_ranges:
            if target_slots:
                break
                
            # 优先从6,7,8,9,10选1个
            available_slots = find_available_slots(driver, time_range_start=current_start, time_range_end=current_end, court_numbers=preferred_courts)
            if available_slots:
                print(f"⚠️ 在{time_label}找到1个时间段")
                target_slots = available_slots[:1]
                break
            
            # 如果还没有，从扩展球场选
            available_slots = find_available_slots(driver, time_range_start=current_start, time_range_end=current_end, court_numbers=extended_courts)
            if available_slots:
                print(f"⚠️ 在{time_label}的扩展球场找到1个时间段")
                target_slots = available_slots[:1]
                break
        
        if not target_slots:
            print(f"❌ 错误: 没有可用时间段")
            return False, 0, []
    
    if not target_slots or len(target_slots) < actual_num_slots:
        print(f"❌ 错误: 可用时间段不足")
        return False, 0, []
    
    selected_count = 0
    booking_details = []  # 记录预订详情
    
    # 选择时间段（点击按钮即可，无需额外点击球场号）
    for elem, time_display, hour, court_num in target_slots:
        if selected_count >= actual_num_slots:
            break
        
        try:
            print(f"\n选择时间段 {selected_count + 1}/{actual_num_slots}: {time_display}")
            
            # 点击按钮（toggleCourt函数会处理选中状态）
            driver.execute_script("arguments[0].click();", elem)
            time.sleep(0.3)
            
            selected_count += 1
            booking_details.append((time_display, court_num))
            print(f"✅ 已成功选择")
            
        except Exception as e:
            print(f"选择失败: {e}")
            continue
    
    if selected_count >= actual_num_slots:
        print(f"\n✅ 成功选择了 {selected_count} 个时间段")
        return True, selected_count, booking_details
    else:
        print(f"\n❌ 只选择了 {selected_count}/{actual_num_slots} 个时间段")
        return False, selected_count, booking_details


def click_book_button(driver):
    """
    点击预订按钮 (实际是 <a> 链接，带有 onclick="book()")
    """
    print("\n正在查找Book按钮...")
    
    # 优先使用最精确的选择器
    selectors = [
        # 最精确：直接匹配实际的Book按钮结构
        "a[onclick='book()']",
        "a.button[onclick='book()']",
        "a.button-3d[onclick='book()']",
        # 备用选择器
        "//a[contains(@onclick, 'book()')]",
        "//a[contains(@class, 'button') and contains(., 'Book')]",
        "a.button:has(span:contains('Book'))",
        # 通用选择器（作为后备）
        "//button[contains(text(), 'Book')]",
        "button[class*='book']",
    ]
    
    for selector in selectors:
        try:
            if selector.startswith("//"):
                elements = driver.find_elements(By.XPATH, selector)
            else:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled():
                    # 验证是Book按钮（包含"Book"文本或有book()函数）
                    text = elem.text.strip()
                    onclick = elem.get_attribute("onclick") or ""
                    
                    if "book" in text.lower() or "book()" in onclick:
                        try:
                            print(f"找到Book按钮: {elem.tag_name}, class={elem.get_attribute('class')}")
                            driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                            time.sleep(0.2)
                            driver.execute_script("arguments[0].click();", elem)
                            time.sleep(0.5)
                            print("✅ 已点击Book按钮")
                            return True
                        except Exception as e:
                            print(f"点击失败，尝试下一个: {e}")
                            continue
        except:
            continue
    
    print("❌ 未找到Book按钮")
    return False


def handle_confirmation_dialog(driver, click_confirm=True):
    """
    处理确认/取消弹出窗口
    确认按钮: <a href="#" data-value="" onclick="bookSubmit()">yes</a>
    """
    time.sleep(0.5)
    
    if click_confirm:
        # 精确匹配确认按钮
        confirm_selectors = [
            "a[onclick='bookSubmit()']",  # 最精确
            "//a[contains(@onclick, 'bookSubmit')]",
            "//a[contains(text(), 'yes')]",
            "//a[contains(text(), 'Yes')]",
        ]
        target_selectors = confirm_selectors
    else:
        # 取消按钮（通常是'no'）
        cancel_selectors = [
            "//a[contains(text(), 'no')]",
            "//a[contains(text(), 'No')]",
            "//a[contains(text(), 'cancel')]",
        ]
        target_selectors = cancel_selectors
    
    for selector in target_selectors:
        try:
            if selector.startswith("//"):
                button = driver.find_element(By.XPATH, selector)
            else:
                button = driver.find_element(By.CSS_SELECTOR, selector)
            
            if button.is_displayed() and button.is_enabled():
                driver.execute_script("arguments[0].click();", button)
                time.sleep(0.5)
                if click_confirm:
                    print("✅ 已确认预订")
                return True
        except:
            continue
    
    return False


def wait_until_target_time(target_hour=8, target_minute=15, target_second=1):
    """
    等待直到指定时间后的几秒
    
    Args:
        target_hour: 目标小时（24小时制）
        target_minute: 目标分钟
        target_second: 目标时间后的秒数
    """
    print(f"\n⏰ 定时模式：等待到 {target_hour:02d}:{target_minute:02d}:{target_second:02d} 自动运行")
    
    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M:%S")
        
        # 检查是否到达目标时间
        if now.hour == target_hour and now.minute == target_minute and now.second >= target_second:
            print(f"\n🎯 已到达目标时间 {current_time_str}，开始预订流程！")
            break
        
        # 每秒更新一次显示
        print(f"\r⏳ 当前时间: {current_time_str} | 目标时间: {target_hour:02d}:{target_minute:02d}:{target_second:02d}", end="", flush=True)
        time.sleep(1)
    
    print()  # 换行


def run_booking_flow(driver, NUM_SLOTS, MAX_RETRIES, RETRY_INTERVAL, CLICK_CONFIRM, time_range_start, time_range_end, alternative_start, alternative_end):
    """
    执行预订流程
    
    Args:
        time_range_start: 首选开始时间（24小时制）
        time_range_end: 首选结束时间（24小时制）
        alternative_start: 备选开始时间（24小时制）
        alternative_end: 备选结束时间（24小时制）
    """
    # 先点击刷新按钮，确保页面是最新的
    print("\n🔄 刷新页面以获取最新时间段...")
    click_refresh_button(driver)
    
    # 记录所有成功预订的时间段
    all_bookings = []
    
    # 重试循环
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n{'='*60}")
        print(f"尝试 {attempt}/{MAX_RETRIES}")
        print(f"{'='*60}\n")
        
        # 选择时间段
        slots_selected, actual_selected, booking_details = select_slots(
            driver, NUM_SLOTS, time_range_start, time_range_end, 
            alternative_start, alternative_end
        )
        
        if not slots_selected:
            print(f"\n⚠️ 尝试 {attempt}: 未能选择足够的时间段")
            
            # 点击刷新按钮重新加载
            if attempt < MAX_RETRIES:
                click_refresh_button(driver)
                print(f"等待 {RETRY_INTERVAL} 秒后重试...")
                time.sleep(RETRY_INTERVAL)
                continue
            else:
                print(f"\n❌ 已尝试 {MAX_RETRIES} 次，均未成功")
                return
        
        # 点击Book按钮
        print(f"\n✅ 已选择 {actual_selected} 个时间段，现在点击Book按钮")
        book_clicked = click_book_button(driver)
        
        if not book_clicked:
            print(f"\n⚠️ 尝试 {attempt}: 未找到Book按钮")
            if attempt < MAX_RETRIES:
                print(f"等待 {RETRY_INTERVAL} 秒后重试...")
                time.sleep(RETRY_INTERVAL)
                continue
            else:
                print(f"\n❌ 已尝试 {MAX_RETRIES} 次，均未找到Book按钮")
                return
        
        # 处理确认弹出窗口
        confirmation_handled = handle_confirmation_dialog(driver, click_confirm=CLICK_CONFIRM)
        
        # 记录本次预订的详情
        all_bookings.extend(booking_details)
        
        print("\n" + "="*60)
        print("✅ 预订流程完成！")
        print("="*60)
        
        # 输出预订汇总
        if all_bookings:
            print(f"\n📊 本次预订汇总：")
            print(f"总共预订了 {len(all_bookings)} 个时间段\n")
            
            # 按球场分组统计
            court_bookings = {}
            for time_display, court_num in all_bookings:
                if court_num not in court_bookings:
                    court_bookings[court_num] = []
                court_bookings[court_num].append(time_display)
            
            # 显示详细信息
            for court_num in sorted(court_bookings.keys()):
                times = court_bookings[court_num]
                print(f"球场 {court_num}: {len(times)} 个时间段")
                for i, time_str in enumerate(times, 1):
                    print(f"  {i}. {time_str}")
                print()
        
        return


def main():
    """主函数"""
    # ========== 配置参数 ==========
    NUM_SLOTS = 2  # 要预订的时间段数量
    USE_EXISTING_BROWSER = True  # 使用已打开的浏览器
    MAX_RETRIES = 5  # 最大重试次数
    RETRY_INTERVAL = 1  # 重试间隔（秒）
    CLICK_CONFIRM = True  # 在弹出窗口中点击确认
    
    print("="*60)
    print("网球场快速预订脚本")
    print("="*60)
    
    # 显示选项菜单
    print("\n请选择运行模式：")
    print("1. 立即开始预订")
    print("2. 定时预订（8:15:01 AM 自动运行）")
    print()
    
    while True:
        choice = input("请输入选项 (1 或 2): ").strip()
        if choice in ['1', '2']:
            break
        print("❌ 无效选项，请输入 1 或 2")
    
    scheduled_mode = (choice == '2')
    
    # 选择时间段
    print("\n请选择预订时间段：")
    print("A. 2:00pm - 6:00pm")
    print("B. 7:00pm - 9:00pm")
    print()
    
    while True:
        time_choice = input("请输入选项 (A 或 B): ").strip().upper()
        if time_choice in ['A', 'B']:
            break
        print("❌ 无效选项，请输入 A 或 B")
    
    # 设置时间范围
    if time_choice == 'A':
        time_range_start = 14  # 2:00pm
        time_range_end = 18    # 6:00pm
        alternative_start = 19  # 5:00pm（备选）
        alternative_end = 21    # 9:00pm（备选）
        time_desc = "2:00pm - 6:00pm"
    else:
        time_range_start = 19  # 5:00pm
        time_range_end = 21    # 9:00pm
        alternative_start = 14  # 2:00pm（备选）
        alternative_end = 18    # 6:00pm（备选）
        time_desc = "5:00pm - 9:00pm"
    
    if USE_EXISTING_BROWSER:
        print("\n请确保：")
        print("1. 已使用远程调试模式启动 Edge 浏览器")
        print("2. 已在浏览器中手动登录到预订网站")
        print("3. 当前页面是预订页面")
        print("4. 已选择好要预订的日期")
    
    print(f"\n已选择时间段: {time_desc}")
    if not scheduled_mode:
        print(f"将尝试 {MAX_RETRIES} 次，每次间隔 {RETRY_INTERVAL} 秒")
    print("="*60)
    
    driver = None
    try:
        driver = setup_driver(use_existing_browser=USE_EXISTING_BROWSER)
        
        print(f"\n当前页面: {driver.current_url}")
        print(f"页面标题: {driver.title}\n")
        
        # 如果是定时模式，等待到指定时间
        if scheduled_mode:
            wait_until_target_time(target_hour=8, target_minute=15, target_second=1)
        
        # 执行预订流程
        run_booking_flow(driver, NUM_SLOTS, MAX_RETRIES, RETRY_INTERVAL, CLICK_CONFIRM, 
                        time_range_start, time_range_end, alternative_start, alternative_end)
        
    except KeyboardInterrupt:
        print("\n\n用户取消")
    except Exception as e:
        print(f"\n❌ 错误: {e}")


if __name__ == "__main__":
    main()


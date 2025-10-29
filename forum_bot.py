#!/usr/bin/env python3
"""
Microsoft Forum Automation Bot
Automates the process of selecting checkboxes and clicking confirm on the Microsoft Forum page.
"""

import time
import logging
import base64
import io
import cv2
import numpy as np
from PIL import Image
import pytesseract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import getpass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MicrosoftForumBot:
    def __init__(self, headless=False):
        """
        Initialize the bot with Chrome WebDriver
        
        Args:
            headless (bool): Run browser in headless mode
        """
        self.driver = None
        self.wait = None
        self.headless = headless
        self.base_url = "https://ixpt.itechwx.com/MicrosoftForum"
        
        # Configure Tesseract OCR (you may need to adjust the path)
        try:
            # Try common Tesseract paths
            tesseract_paths = [
                '/usr/local/bin/tesseract',
                '/opt/homebrew/bin/tesseract',
                '/usr/bin/tesseract',
                'tesseract'  # If it's in PATH
            ]
            
            for path in tesseract_paths:
                try:
                    pytesseract.pytesseract.tesseract_cmd = path
                    # Test if tesseract works
                    pytesseract.get_tesseract_version()
                    logger.info(f"Tesseract OCR configured at: {path}")
                    break
                except:
                    continue
            else:
                logger.warning("Tesseract not found. CAPTCHA reading will not work.")
        except Exception as e:
            logger.warning(f"Tesseract configuration failed: {e}")
    
    def read_captcha_from_canvas(self):
        """
        Read CAPTCHA text from canvas element using OCR with multiple strategies
        
        Returns:
            str: The CAPTCHA text, or None if reading failed
        """
        try:
            logger.info("Starting CAPTCHA detection...")
            
            # Wait for page to fully load
            time.sleep(2)
            
            # Find the canvas element with multiple strategies
            canvas_selectors = [
                "canvas",
                "img[src*='captcha']",
                "img[src*='verification']",
                "div[style*='background']",
                "div[class*='captcha']",
                "div[class*='verification']",
                "div[id*='captcha']",
                "div[id*='verification']",
                "img[alt*='captcha']",
                "img[alt*='verification']"
            ]
            
            canvas_element = None
            found_selector = None
            
            for selector in canvas_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    
                    for element in elements:
                        try:
                            # Check if element is visible and has reasonable size
                            if element.is_displayed():
                                size = element.size
                                logger.info(f"Element size: {size}")
                                if size['width'] > 30 and size['height'] > 15:
                                    canvas_element = element
                                    found_selector = selector
                                    logger.info(f"✅ Found CAPTCHA element with selector: {selector}")
                                    break
                        except Exception as e:
                            logger.warning(f"Error checking element: {e}")
                            continue
                    
                    if canvas_element:
                        break
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue
            
            if not canvas_element:
                logger.error("❌ CAPTCHA canvas element not found")
                # Let's try to find any image-like element
                try:
                    all_images = self.driver.find_elements(By.TAG_NAME, "img")
                    logger.info(f"Found {len(all_images)} img elements total")
                    for img in all_images:
                        if img.is_displayed():
                            logger.info(f"Image src: {img.get_attribute('src')}")
                            logger.info(f"Image alt: {img.get_attribute('alt')}")
                except Exception as e:
                    logger.warning(f"Error listing images: {e}")
                return None
            
            # Scroll to element to ensure it's fully visible
            self.driver.execute_script("arguments[0].scrollIntoView(true);", canvas_element)
            time.sleep(1)
            
            # Take screenshot of the canvas element
            logger.info("Taking screenshot of CAPTCHA element...")
            canvas_screenshot = canvas_element.screenshot_as_png
            logger.info(f"Screenshot size: {len(canvas_screenshot)} bytes")
            
            # Convert to PIL Image
            image = Image.open(io.BytesIO(canvas_screenshot))
            logger.info(f"Image dimensions: {image.size}")
            
            # Save debug image
            try:
                image.save("debug_captcha.png")
                logger.info("Saved debug image as debug_captcha.png")
            except Exception as e:
                logger.warning(f"Could not save debug image: {e}")
            
            # Try multiple image processing strategies
            strategies = [
                self._process_image_strategy_1,
                self._process_image_strategy_2,
                self._process_image_strategy_3,
                self._process_image_strategy_4,
                self._process_image_strategy_5  # New strategy for digit-by-digit reading
            ]
            
            for i, strategy in enumerate(strategies, 1):
                try:
                    logger.info(f"Trying strategy {i}...")
                    processed_image = strategy(image)
                    
                    # Special handling for strategy 5 (digit-by-digit)
                    if i == 5 and isinstance(processed_image, str):
                        captcha_text = processed_image
                    else:
                        captcha_text = self._extract_text_from_image(processed_image)
                    
                    if captcha_text and len(captcha_text) >= 3:  # Minimum 3 digits
                        logger.info(f"✅ CAPTCHA read successfully with strategy {i}: {captcha_text}")
                        return captcha_text
                    else:
                        logger.warning(f"Strategy {i} result: '{captcha_text}' (too short)")
                except Exception as e:
                    logger.warning(f"Strategy {i} failed: {e}")
                    continue
            
            logger.warning("❌ All CAPTCHA reading strategies failed")
            return None
                
        except Exception as e:
            logger.error(f"❌ Error reading CAPTCHA: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def _process_image_strategy_1(self, image):
        """Strategy 1: Basic threshold processing with rotation correction"""
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Try to correct rotation
        gray = self._correct_rotation(gray)
        
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    
    def _correct_rotation(self, gray_image):
        """Try to correct rotation in the image"""
        try:
            # Find contours
            contours, _ = cv2.findContours(gray_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Get the largest contour (likely the text)
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Get the minimum area rectangle
                rect = cv2.minAreaRect(largest_contour)
                angle = rect[2]
                
                # Correct the angle if it's significant
                if abs(angle) > 5:
                    # Rotate the image to correct the angle
                    (h, w) = gray_image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, -angle, 1.0)
                    gray_image = cv2.warpAffine(gray_image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return gray_image
        except Exception as e:
            logger.warning(f"Rotation correction failed: {e}")
            return gray_image
    
    def _process_image_strategy_2(self, image):
        """Strategy 2: Adaptive threshold with noise removal"""
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive threshold
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        
        # Remove noise
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        return cleaned
    
    def _process_image_strategy_3(self, image):
        """Strategy 3: High contrast processing"""
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Apply threshold
        _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh
    
    def _process_image_strategy_4(self, image):
        """Strategy 4: Edge detection and morphological operations"""
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # Edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilate edges
        kernel = np.ones((2,2), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        return dilated
    
    def _process_image_strategy_5(self, image):
        """Strategy 5: Digit-by-digit reading with position detection and color handling"""
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Try different color channel extractions for colored digits
        strategies = [
            # Strategy 1: Convert to grayscale
            cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY),
            # Strategy 2: Extract red channel (for red digits)
            opencv_image[:, :, 2],
            # Strategy 3: Extract green channel (for green digits)
            opencv_image[:, :, 1],
            # Strategy 4: Extract blue channel (for blue digits)
            opencv_image[:, :, 0],
            # Strategy 5: Convert to HSV and extract value channel
            cv2.cvtColor(opencv_image, cv2.COLOR_BGR2HSV)[:, :, 2]
        ]
        
        best_result = None
        best_confidence = 0
        
        for i, gray in enumerate(strategies):
            try:
                # Apply threshold
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Find contours to separate individual digits
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Filter contours by size (should be roughly digit-sized)
                digit_contours = []
                for contour in contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    # Filter by size - digits should be reasonable size
                    if w > 8 and h > 12 and w < 40 and h < 35:
                        digit_contours.append((x, y, w, h, contour))
                
                # Sort by x position (left to right)
                digit_contours.sort(key=lambda x: x[0])
                
                # Extract individual digits
                digits = []
                for x, y, w, h, contour in digit_contours:
                    # Extract the digit region
                    digit_roi = thresh[y:y+h, x:x+w]
                    
                    # Resize to standard size for better OCR
                    digit_roi = cv2.resize(digit_roi, (20, 30))
                    
                    # Use OCR on individual digit with multiple configs
                    digit_configs = [
                        r'--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789',
                        r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',
                        r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
                    ]
                    
                    digit_text = None
                    for config in digit_configs:
                        try:
                            result = pytesseract.image_to_string(digit_roi, config=config).strip()
                            result = ''.join(filter(str.isdigit, result))
                            if result and len(result) == 1:
                                digit_text = result
                                break
                        except:
                            continue
                    
                    if digit_text:
                        digits.append(digit_text)
                
                # Combine digits in order
                if digits and len(digits) >= 3:
                    combined = ''.join(digits)
                    confidence = len(digits)  # More digits = higher confidence
                    if confidence > best_confidence:
                        best_result = combined
                        best_confidence = confidence
                        logger.info(f"Strategy {i+1} digit-by-digit reading result: {combined} (confidence: {confidence})")
                
            except Exception as e:
                logger.warning(f"Strategy {i+1} failed: {e}")
                continue
        
        if best_result:
            return best_result
        
        return thresh
    
    def _extract_text_from_image(self, processed_image):
        """Extract text from processed image using multiple OCR configurations"""
        ocr_configs = [
            r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789',
            r'--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789',  # Single character
            r'--oem 3 --psm 8',  # Without whitelist
            r'--oem 3 --psm 7',  # Without whitelist
            r'--oem 3 --psm 6',  # Without whitelist
            r'--oem 3 --psm 10'  # Single character without whitelist
        ]
        
        for i, config in enumerate(ocr_configs, 1):
            try:
                logger.info(f"Trying OCR config {i}: {config}")
                captcha_text = pytesseract.image_to_string(processed_image, config=config).strip()
                logger.info(f"Raw OCR result: '{captcha_text}'")
                
                # Clean up the text (remove spaces, keep only digits)
                captcha_text = ''.join(filter(str.isdigit, captcha_text))
                logger.info(f"Cleaned OCR result: '{captcha_text}'")
                
                if captcha_text and len(captcha_text) >= 3:
                    logger.info(f"✅ Valid CAPTCHA found: {captcha_text}")
                    return captcha_text
                else:
                    logger.warning(f"OCR config {i} result too short: '{captcha_text}'")
            except Exception as e:
                logger.warning(f"OCR config {i} failed: {e}")
                continue
        
        logger.warning("❌ All OCR configurations failed")
        return None
    
    def read_captcha_from_img(self):
        """
        Alternative method to read CAPTCHA from img element
        
        Returns:
            str: The CAPTCHA text, or None if reading failed
        """
        try:
            # Look for img elements that might contain the CAPTCHA
            img_selectors = [
                "img[src*='captcha']",
                "img[src*='verification']",
                "img[alt*='captcha']",
                "img[alt*='verification']"
            ]
            
            img_element = None
            for selector in img_selectors:
                try:
                    img_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not img_element:
                return None
            
            # Get the image source
            img_src = img_element.get_attribute('src')
            
            if img_src.startswith('data:image'):
                # Handle base64 encoded images
                header, encoded = img_src.split(',', 1)
                image_data = base64.b64decode(encoded)
                image = Image.open(io.BytesIO(image_data))
            else:
                # Handle regular image URLs
                import requests
                response = requests.get(img_src)
                image = Image.open(io.BytesIO(response.content))
            
            # Convert to OpenCV format and process
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Use Tesseract to read the text
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789'
            captcha_text = pytesseract.image_to_string(thresh, config=custom_config).strip()
            captcha_text = ''.join(filter(str.isdigit, captcha_text))
            
            if captcha_text:
                logger.info(f"CAPTCHA read from img: {captcha_text}")
                return captcha_text
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error reading CAPTCHA from img: {e}")
            return None
    
    def refresh_captcha(self):
        """
        Try to refresh the CAPTCHA by clicking refresh button or reloading page
        """
        try:
            # Look for refresh button
            refresh_selectors = [
                "button[title*='refresh']",
                "button[title*='Refresh']",
                "button[class*='refresh']",
                "button[class*='reload']",
                "img[alt*='refresh']",
                "img[alt*='Refresh']",
                "a[href*='captcha']",
                "a[href*='verification']"
            ]
            
            for selector in refresh_selectors:
                try:
                    refresh_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if refresh_button.is_displayed():
                        logger.info("Found refresh button, clicking to get new CAPTCHA...")
                        refresh_button.click()
                        time.sleep(2)
                        return True
                except NoSuchElementException:
                    continue
            
            # If no refresh button found, try to reload the page
            logger.info("No refresh button found, reloading page...")
            self.driver.refresh()
            time.sleep(3)
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing CAPTCHA: {e}")
            return False
        
    def setup_driver(self):
        """Set up Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Additional Chrome options for better compatibility
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        try:
            # Use webdriver-manager to automatically download and manage ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise
    
    def login(self, username, password, verification_code=None):
        """
        Login to the Microsoft Forum with verification code
        
        Args:
            username (str): Username for login
            password (str): Password for login
            verification_code (str): Canvas-based verification code (if None, will prompt user)
        """
        try:
            # Navigate to login page first
            login_url = "https://ixpt.itechwx.com/login"
            logger.info(f"Navigating to login page: {login_url}")
            self.driver.get(login_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Look for login form elements with various possible selectors
            username_selectors = [
                "input[placeholder*='account']",
                "input[placeholder*='Account']",
                "input[name='username']",
                "input[name='account']",
                "input[type='text']",
                "input[placeholder*='Please input account']",
                "input[placeholder*='please input account']"
            ]
            
            password_selectors = [
                "input[placeholder*='password']",
                "input[placeholder*='Password']",
                "input[name='password']",
                "input[type='password']",
                "input[placeholder*='Please input password']",
                "input[placeholder*='please input password']"
            ]
            
            verification_selectors = [
                "input[placeholder*='verification']",
                "input[placeholder*='Verification']",
                "input[name='verification']",
                "input[name='captcha']",
                "input[placeholder*='Verification code']",
                "input[placeholder*='verification code']"
            ]
            
            # Find username field
            username_field = None
            logger.info("Looking for username field...")
            for selector in username_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with username selector: {selector}")
                    for element in elements:
                        if element.is_displayed():
                            username_field = element
                            logger.info(f"✅ Found username field with selector: {selector}")
                            break
                    if username_field:
                        break
                except NoSuchElementException:
                    continue
            
            if not username_field:
                logger.error("❌ Username field not found")
                # Debug: list all input elements
                try:
                    all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                    logger.info(f"Found {len(all_inputs)} input elements total:")
                    for i, inp in enumerate(all_inputs):
                        if inp.is_displayed():
                            placeholder = inp.get_attribute('placeholder')
                            name = inp.get_attribute('name')
                            input_type = inp.get_attribute('type')
                            logger.info(f"  Input {i+1}: type='{input_type}', name='{name}', placeholder='{placeholder}'")
                except Exception as e:
                    logger.warning(f"Error listing inputs: {e}")
                raise Exception("Username field not found")
            
            # Find password field
            password_field = None
            logger.info("Looking for password field...")
            for selector in password_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with password selector: {selector}")
                    for element in elements:
                        if element.is_displayed():
                            password_field = element
                            logger.info(f"✅ Found password field with selector: {selector}")
                            break
                    if password_field:
                        break
                except NoSuchElementException:
                    continue
            
            if not password_field:
                logger.error("❌ Password field not found")
                raise Exception("Password field not found")
            
            # Find verification code field
            verification_field = None
            logger.info("Looking for verification code field...")
            for selector in verification_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with verification selector: {selector}")
                    for element in elements:
                        if element.is_displayed():
                            verification_field = element
                            logger.info(f"✅ Found verification field with selector: {selector}")
                            break
                    if verification_field:
                        break
                except NoSuchElementException:
                    continue
            
            if not verification_field:
                logger.error("❌ Verification code field not found")
                raise Exception("Verification code field not found")
            
            # Enter credentials
            logger.info("Entering username...")
            username_field.clear()
            username_field.send_keys(username)
            
            logger.info("Entering password...")
            password_field.clear()
            password_field.send_keys(password)
            
            # Handle verification code - MANUAL ENTRY (more reliable)
            if verification_code is None:
                logger.info("Please manually enter the CAPTCHA code shown in the browser.")
                logger.info("Look at the browser window and type the CAPTCHA code.")
                
                # Keep browser open and wait for manual input
                try:
                    verification_code = input("Enter the CAPTCHA code from the browser: ").strip()
                    if verification_code and len(verification_code) >= 3:
                        logger.info(f"Using manually entered CAPTCHA: {verification_code}")
                    else:
                        logger.error("Invalid CAPTCHA code entered")
                        raise Exception("Invalid CAPTCHA code")
                except KeyboardInterrupt:
                    logger.info("User cancelled CAPTCHA entry")
                    raise Exception("CAPTCHA entry cancelled by user")
                except Exception as e:
                    logger.error(f"Error getting manual CAPTCHA input: {e}")
                    raise Exception("Failed to get manual CAPTCHA input")
            
            logger.info("Entering verification code...")
            verification_field.clear()
            verification_field.send_keys(verification_code)
            
            # Find and click sign in button
            signin_selectors = [
                "//button[contains(text(), 'Sign In')]",
                "//input[@value='Sign In']",
                "//button[@type='submit']",
                "//input[@type='submit']",
                "//button[contains(text(), 'Login')]",
                "//button[contains(text(), '登录')]",
                "button[type='submit']",
                "input[type='submit']"
            ]
            
            signin_button = None
            for selector in signin_selectors:
                try:
                    if selector.startswith("//"):
                        # XPath selector
                        signin_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        # CSS selector
                        signin_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not signin_button:
                raise Exception("Sign in button not found")
            
            logger.info("Clicking sign in button...")
            signin_button.click()
            
            # Wait for login to complete and redirect
            time.sleep(5)
            
            # Check if we're redirected to the forum page
            current_url = self.driver.current_url
            if "MicrosoftForum" in current_url or "login" not in current_url:
                logger.info("Login completed successfully")
                return True
            else:
                logger.warning("Login may have failed - still on login page")
                return False
            
        except TimeoutException:
            logger.warning("Login form not found - may already be logged in or page structure is different")
            return False
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def select_first_checkbox(self):
        """
        Select the first checkbox in the first row only
        """
        try:
            # Wait for table to load
            time.sleep(1)
            
            # Find the first checkbox using the exact structure from your HTML
            checkbox = self.driver.find_element(By.XPATH, "//tr[@class='ant-table-row ant-table-row-level-0']//input[@type='checkbox']")
            
            if not checkbox.is_selected():
                logger.info("🎯 Clicking first checkbox...")
                
                # Scroll to checkbox
                self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                time.sleep(0.5)
                
                # Click the label wrapper (this is what works for Ant Design)
                label = self.driver.find_element(By.XPATH, "//tr[@class='ant-table-row ant-table-row-level-0']//label[@class='ant-checkbox-wrapper']")
                label.click()
                time.sleep(0.5)
                
                if checkbox.is_selected():
                    logger.info("✅ Checkbox selected successfully")
                    return 1
                else:
                    logger.warning("⚠️ Checkbox click failed, trying direct input click")
                    checkbox.click()
                    time.sleep(0.5)
                    if checkbox.is_selected():
                        logger.info("✅ Checkbox selected with direct click")
                        return 1
            else:
                logger.info("Checkbox already selected")
                return 1
                
        except Exception as e:
            logger.error(f"Error selecting checkbox: {e}")
            return 0
    
    def _try_checkbox_selection_strategies(self, checkbox, checkbox_num):
        """
        Try multiple strategies to select a checkbox
        """
        strategies = [
            self._strategy_click_wrapper,
            self._strategy_click_inner_span,
            self._strategy_click_cell,
            self._strategy_click_row,
            self._strategy_click_input_direct,
            self._strategy_javascript_click,
            self._strategy_javascript_set_checked,
            self._strategy_force_click,
            self._strategy_simulate_user_action
        ]
        
        for i, strategy in enumerate(strategies, 1):
            try:
                logger.info(f"  Trying strategy {i}...")
                if strategy(checkbox):
                    if checkbox.is_selected():
                        logger.info(f"✅ Checkbox {checkbox_num} selected successfully with strategy {i}")
                        return True
                    else:
                        logger.warning(f"⚠️ Strategy {i} executed but checkbox not selected")
                else:
                    logger.warning(f"⚠️ Strategy {i} failed")
            except Exception as e:
                logger.warning(f"⚠️ Strategy {i} error: {e}")
                continue
        
        logger.error(f"❌ All strategies failed for checkbox {checkbox_num}")
        return False
    
    def _strategy_click_wrapper(self, checkbox):
        """Strategy 1: Click the wrapper element (Ant Design pattern)"""
        try:
            # First try to find the exact wrapper structure from the HTML
            wrapper_selectors = [
                # Exact match for the provided HTML structure
                "//label[@class='ant-checkbox-wrapper'][.//input[@type='checkbox']]",
                "//td[@class='ant-table-cell ant-table-selection-column']//label[@class='ant-checkbox-wrapper']",
                "//tr[@class='ant-table-row ant-table-row-level-0']//label[@class='ant-checkbox-wrapper']",
                # Broader selectors
                "//span[contains(@class, 'ant-checkbox-wrapper')][.//input[@type='checkbox']]",
                "//span[contains(@class, 'ant-checkbox')][.//input[@type='checkbox']]"
            ]
            
            for selector in wrapper_selectors:
                try:
                    wrappers = self.driver.find_elements(By.XPATH, selector)
                    logger.info(f"    Found {len(wrappers)} wrappers with selector: {selector}")
                    
                    for j, wrapper in enumerate(wrappers):
                        try:
                            # Check if this wrapper contains our specific checkbox
                            wrapper_inputs = wrapper.find_elements(By.XPATH, ".//input[@type='checkbox']")
                            if checkbox in wrapper_inputs:
                                logger.info(f"    Clicking wrapper {j+1} that contains our checkbox")
                                # Scroll to wrapper first
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", wrapper)
                                time.sleep(0.2)
                                wrapper.click()
                                time.sleep(0.5)
                                return True
                        except Exception as e:
                            logger.warning(f"    Error checking wrapper {j+1}: {e}")
                            continue
                except Exception as e:
                    logger.warning(f"    Error with selector {selector}: {e}")
                    continue
            
            # Fallback: find wrapper using JavaScript - more specific to the structure
            logger.info("    Trying JavaScript wrapper detection...")
            wrapper = self.driver.execute_script("""
                var input = arguments[0];
                // Look for the label with ant-checkbox-wrapper class
                var parent = input.parentElement;
                while (parent) {
                    if (parent.tagName === 'LABEL' && parent.classList.contains('ant-checkbox-wrapper')) {
                        return parent;
                    }
                    parent = parent.parentElement;
                }
                return null;
            """, checkbox)
            
            if wrapper:
                logger.info("    Found wrapper via JavaScript, clicking...")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", wrapper)
                time.sleep(0.2)
                wrapper.click()
                time.sleep(0.5)
                return True
            else:
                logger.warning("    No wrapper found via JavaScript")
                
        except Exception as e:
            logger.warning(f"Wrapper click strategy failed: {e}")
        
        return False
    
    def _strategy_click_inner_span(self, checkbox):
        """Strategy 2: Click the ant-checkbox-inner span (visual checkbox)"""
        try:
            # Find the ant-checkbox-inner span that's a sibling of the input
            inner_span = self.driver.execute_script("""
                var input = arguments[0];
                var parent = input.parentElement;
                if (parent) {
                    var spans = parent.getElementsByClassName('ant-checkbox-inner');
                    if (spans.length > 0) {
                        return spans[0];
                    }
                }
                return null;
            """, checkbox)
            
            if inner_span:
                logger.info("    Found ant-checkbox-inner span, clicking...")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", inner_span)
                time.sleep(0.2)
                inner_span.click()
                time.sleep(0.5)
                return True
            else:
                logger.warning("    No ant-checkbox-inner span found")
                
        except Exception as e:
            logger.warning(f"Inner span click strategy failed: {e}")
        
        return False
    
    def _strategy_click_cell(self, checkbox):
        """Strategy 3: Click the table cell containing the checkbox"""
        try:
            # Find the table cell that contains this checkbox
            cell = self.driver.execute_script("""
                var input = arguments[0];
                var parent = input.parentElement;
                while (parent && parent.tagName !== 'TD') {
                    parent = parent.parentElement;
                }
                return parent;
            """, checkbox)
            
            if cell:
                logger.info("    Found table cell, clicking...")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", cell)
                time.sleep(0.2)
                cell.click()
                time.sleep(0.5)
                return True
            else:
                logger.warning("    No table cell found")
                
        except Exception as e:
            logger.warning(f"Cell click strategy failed: {e}")
        
        return False
    
    def _strategy_click_row(self, checkbox):
        """Strategy 2: Click the table row containing the checkbox"""
        try:
            # Find the table row that contains this checkbox
            row = self.driver.execute_script("""
                var input = arguments[0];
                var parent = input.parentElement;
                while (parent && parent.tagName !== 'TR') {
                    parent = parent.parentElement;
                }
                return parent;
            """, checkbox)
            
            if row:
                logger.info("    Found table row, clicking...")
                row.click()
                time.sleep(0.5)
                return True
            else:
                logger.warning("    No table row found")
                
        except Exception as e:
            logger.warning(f"Row click strategy failed: {e}")
        
        return False
    
    def _strategy_click_input_direct(self, checkbox):
        """Strategy 2: Click the input directly"""
        try:
            checkbox.click()
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.warning(f"Direct input click failed: {e}")
            return False
    
    def _strategy_javascript_click(self, checkbox):
        """Strategy 3: JavaScript click"""
        try:
            self.driver.execute_script("arguments[0].click();", checkbox)
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.warning(f"JavaScript click failed: {e}")
            return False
    
    def _strategy_javascript_set_checked(self, checkbox):
        """Strategy 4: Set checked property and trigger events"""
        try:
            self.driver.execute_script("""
                arguments[0].checked = true;
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('click', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            """, checkbox)
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.warning(f"JavaScript set checked failed: {e}")
            return False
    
    def _strategy_force_click(self, checkbox):
        """Strategy 5: Force click with multiple methods"""
        try:
            # Try ActionChains
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element(checkbox).click().perform()
            time.sleep(0.3)
            return True
        except Exception as e:
            logger.warning(f"Force click failed: {e}")
            return False
    
    def _strategy_simulate_user_action(self, checkbox):
        """Strategy 6: Simulate complete user action"""
        try:
            # Focus the element first
            self.driver.execute_script("arguments[0].focus();", checkbox)
            time.sleep(0.1)
            
            # Mouse over
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.move_to_element(checkbox).perform()
            time.sleep(0.1)
            
            # Click with mouse
            actions.click(checkbox).perform()
            time.sleep(0.3)
            
            # Also trigger keyboard space
            checkbox.send_keys(" ")
            time.sleep(0.3)
            
            return True
        except Exception as e:
            logger.warning(f"Simulate user action failed: {e}")
            return False
    
    def click_confirm(self):
        """
        Click the confirm button
        """
        try:
            # Look for confirm button with exact selectors from the HTML
            confirm_selectors = [
                "//button[@class='ant-btn ant-btn-primary Confirm_bottom']",
                "//button[contains(@class, 'Confirm_bottom')]",
                "//button[@class='ant-btn ant-btn-primary']//span[text()='Confirm']",
                "//button[contains(@class, 'ant-btn-primary')]//span[text()='Confirm']",
                "//button[text()='Confirm']",
                "//button[contains(text(), 'Confirm')]",
                "//button[contains(text(), 'confirm')]",
                "//button[contains(@class, 'confirm')]",
                "//button[contains(@class, 'ant-btn-primary')]",
                "//input[@value='Confirm']",
                "//input[@value='confirm']",
                "//button[contains(@class, 'ant-btn') and contains(@class, 'primary')]"
            ]
            
            confirm_button = None
            for selector in confirm_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            confirm_button = element
                            logger.info(f"Found confirm button with selector: {selector}")
                            break
                    if confirm_button:
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} failed: {e}")
                    continue
            
            if confirm_button:
                # Scroll to button if needed
                self.driver.execute_script("arguments[0].scrollIntoView(true);", confirm_button)
                time.sleep(0.2)
                
                # Try multiple click methods
                try:
                    confirm_button.click()
                    logger.info("✅ Confirm button clicked successfully")
                except:
                    # If normal click fails, try JavaScript click
                    self.driver.execute_script("arguments[0].click();", confirm_button)
                    logger.info("✅ Confirm button clicked with JavaScript")
                
                return True
            else:
                logger.error("❌ Confirm button not found")
                return False
                
        except Exception as e:
            logger.error(f"Error clicking confirm button: {e}")
            return False
    
    def run_automation_cycle(self):
        """
        Run one complete automation cycle: navigate to forum, select checkboxes and click confirm
        """
        try:
            logger.info("Starting automation cycle")
            
            # Navigate to the Microsoft Forum page
            logger.info(f"Navigating to {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(3)
            
            # Check if we're logged in by looking for login elements
            try:
                signin_elements = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign In')]")
                if signin_elements and any(elem.is_displayed() for elem in signin_elements):
                    logger.warning("Not logged in - found Sign In button")
                    return False
            except:
                pass
            
            # Select all checkboxes
            selected_count = self.select_first_checkbox()
            
            if selected_count > 0:
                # Click confirm button
                if self.click_confirm():
                    logger.info("Automation cycle completed successfully")
                    return True
                else:
                    logger.error("Failed to click confirm button")
                    return False
            else:
                logger.warning("No checkboxes were selected")
                return False
                
        except Exception as e:
            logger.error(f"Automation cycle failed: {e}")
            return False
    
    def run_continuous(self, interval_seconds=60):
        """
        Run automation continuously with specified interval
        
        Args:
            interval_seconds (int): Time between automation cycles in seconds
        """
        logger.info(f"Starting continuous automation with {interval_seconds} second intervals")
        
        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                logger.info(f"Starting cycle {cycle_count}")
                
                # Run one automation cycle
                success = self.run_automation_cycle()
                
                if success:
                    logger.info(f"Cycle {cycle_count} completed successfully")
                else:
                    logger.warning(f"Cycle {cycle_count} had issues")
                
                # Wait for next cycle
                logger.info(f"Waiting {interval_seconds} seconds before next cycle...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Automation stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in cycle {cycle_count}: {e}")
                time.sleep(5)  # Short wait before retrying
    
    def continuous_monitor(self, interval_seconds=1):
        """
        Continuously monitor for new cases with specified interval
        
        Args:
            interval_seconds (int): Time between checks in seconds (default: 1)
        """
        logger.info(f"Starting continuous monitoring with {interval_seconds} second intervals")
        logger.info("Press Ctrl+C to stop monitoring")
        
        cycle_count = 0
        last_case_count = 0
        
        while True:
            try:
                cycle_count += 1
                logger.info(f"🔍 Check #{cycle_count} - {time.strftime('%H:%M:%S')}")
                
                # Navigate to forum page
                self.driver.get(self.base_url)
                time.sleep(1)  # Wait for page to load
                
                # Check if we're still logged in
                current_url = self.driver.current_url
                if "login" in current_url:
                    logger.warning("❌ Not logged in - redirecting to login page")
                    logger.info("Please login manually in the browser window")
                    time.sleep(10)  # Wait for manual login
                    continue
                
                # Check for checkboxes (cases) - use simple approach
                try:
                    # Find checkboxes using the exact structure
                    checkboxes = self.driver.find_elements(By.XPATH, "//tr[@class='ant-table-row ant-table-row-level-0']//input[@type='checkbox']")
                    current_case_count = len(checkboxes)
                    logger.info(f"📊 Total cases found: {current_case_count}")
                    
                    # Debug: show details of each checkbox
                    for i, cb in enumerate(checkboxes):
                        is_selected = cb.is_selected()
                        logger.info(f"  Checkbox {i+1}: selected={is_selected}")
                    
                    # If no checkboxes found, show debugging info
                    if current_case_count == 0:
                        logger.warning("No checkboxes found - debugging page content...")
                        try:
                            all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                            logger.info(f"Found {len(all_inputs)} input elements total:")
                            for i, inp in enumerate(all_inputs):
                                if inp.is_displayed():
                                    input_type = inp.get_attribute('type')
                                    input_class = inp.get_attribute('class')
                                    input_id = inp.get_attribute('id')
                                    logger.info(f"  Input {i+1}: type='{input_type}', class='{input_class}', id='{input_id}'")
                            
                            # Also check current URL
                            current_url = self.driver.current_url
                            logger.info(f"Current URL: {current_url}")
                            
                            # Check page title
                            page_title = self.driver.title
                            logger.info(f"Page title: {page_title}")
                            
                            # Check for any elements with 'checkbox' in class name
                            checkbox_elements = self.driver.find_elements(By.XPATH, "//*[contains(@class, 'checkbox')]")
                            logger.info(f"Found {len(checkbox_elements)} elements with 'checkbox' in class:")
                            for i, elem in enumerate(checkbox_elements):
                                if elem.is_displayed():
                                    tag_name = elem.tag_name
                                    elem_class = elem.get_attribute('class')
                                    logger.info(f"  Element {i+1}: <{tag_name}> class='{elem_class}'")
                            
                            # Check for any table or list elements
                            tables = self.driver.find_elements(By.TAG_NAME, "table")
                            logger.info(f"Found {len(tables)} table elements")
                            
                            # Check page source for 'checkbox' text
                            page_source = self.driver.page_source
                            if 'checkbox' in page_source.lower():
                                logger.info("✅ Found 'checkbox' text in page source")
                            else:
                                logger.warning("❌ No 'checkbox' text found in page source")
                            
                        except Exception as e:
                            logger.warning(f"Error listing inputs: {e}")
                    
                    if current_case_count > 0:
                        if current_case_count != last_case_count:
                            logger.info(f"🆕 New cases detected! ({last_case_count} → {current_case_count})")
                            last_case_count = current_case_count
                        
                        logger.info("Processing cases...")
                        
                        # Select all checkboxes
                        selected_count = self.select_first_checkbox()
                        
                        if selected_count > 0:
                            logger.info(f"Selected {selected_count} checkboxes")
                            
                            # Click confirm
                            if self.click_confirm():
                                logger.info("Confirmed successfully!")
                            else:
                                logger.error("Failed to click confirm")
                        else:
                            logger.warning("No checkboxes were selected")
                    else:
                        logger.info("No cases found")
                        last_case_count = 0
                        
                except Exception as e:
                    logger.error(f"Error checking cases: {e}")
                
                logger.info(f"Waiting {interval_seconds} second(s)...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                logger.info("Retrying in 5 seconds...")
                time.sleep(5)
    
    def close(self):
        """Close the browser and cleanup"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

def main():
    """Main function to run the bot"""
    print("Microsoft Forum Automation Bot")
    print("=" * 40)
    
    # Hardcoded credentials
    username = "henry.mai"
    password = "abc@123456"
    
    # Always run with browser visible for CAPTCHA entry
    headless = False
    print("Browser will be visible for CAPTCHA entry")
    
    # Fixed interval
    interval = 60
    
    # Initialize and run bot
    bot = MicrosoftForumBot(headless=headless)
    
    try:
        bot.setup_driver()
        
        # Login with verification code handling
        login_success = bot.login(username, password)
        
        if not login_success:
            print("Login failed. Please check your credentials and try again.")
            return
        
        # Start continuous monitoring (1 second intervals)
        print("\nStarting continuous monitoring...")
        print("Checking for cases every 1 second...")
        print("Press Ctrl+C to stop")
        bot.continuous_monitor(1)  # 1 second intervals
            
    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
    finally:
        bot.close()

if __name__ == "__main__":
    main()

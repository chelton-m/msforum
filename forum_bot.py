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
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager


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
            # Look for canvas elements specifically first
            canvas_selectors = [
                "canvas",
            ]

            # First try canvas elements only
            for selector in canvas_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")

                    for element in elements:
                        try:
                            if element.is_displayed():
                                size = element.size
                                logger.info(f"Canvas element size: {size}")
                                # Canvas should be relatively small (CAPTCHA size)
                                if size['width'] > 20 and size['width'] < 200 and size['height'] > 10 and size['height'] < 100:
                                    canvas_element = element
                                    logger.info(f"✅ Found CAPTCHA canvas element")
                                    break
                        except Exception as e:
                            logger.warning(f"Error checking element: {e}")
                            continue

                    if canvas_element:
                        break
                except Exception as e:
                    logger.warning(f"Error with selector {selector}: {e}")
                    continue

            # If canvas not found, try img elements as fallback
            if not canvas_element:
                img_selectors = [
                    "img[src*='captcha']",
                    "img[src*='verification']",
                    "img[alt*='captcha']",
                    "img[alt*='verification']"
                ]
                for selector in img_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")

                        for element in elements:
                            try:
                                if element.is_displayed():
                                    size = element.size
                                    logger.info(f"Img element size: {size}")
                                    if size['width'] > 20 and size['width'] < 200 and size['height'] > 10 and size['height'] < 100:
                                        canvas_element = element
                                        logger.info(f"✅ Found CAPTCHA img element")
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
            # Strategy 5: Convert to LAB and extract L channel (better for color separation)
            cv2.cvtColor(opencv_image, cv2.COLOR_BGR2LAB)[:, :, 0],
            # Strategy 6: Convert to HSV and extract value channel
            cv2.cvtColor(opencv_image, cv2.COLOR_BGR2HSV)[:, :, 2]
        ]
        
        best_result = None
        best_confidence = 0
        
        for i, gray in enumerate(strategies):
            try:
                # Try multiple threshold methods
                # Method 1: OTSU threshold
                _, thresh1 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Method 2: Adaptive threshold for better handling of varying lighting
                thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                               cv2.THRESH_BINARY, 11, 2)
                
                # Method 3: Inverted OTSU
                _, thresh3 = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                
                # Method 4: Inverted adaptive
                thresh4 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                               cv2.THRESH_BINARY_INV, 11, 2)

                thresh_options = [thresh1, thresh2, thresh3, thresh4]

                # Try each threshold method
                for thresh_idx, thresh in enumerate(thresh_options):
                    try:
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
                        
                        # Combine digits in order - CAPTCHA should be exactly 4 digits
                        if digits and len(digits) == 4:
                            combined = ''.join(digits)
                            confidence = len(digits)  # More digits = higher confidence
                            if confidence > best_confidence:
                                best_result = combined
                                best_confidence = confidence
                                logger.info(f"Strategy {i+1} digit-by-digit reading result: {combined} (confidence: {confidence})")
                    except Exception as e:
                        logger.warning(f"Threshold method {thresh_idx+1} failed: {e}")
                        continue
                
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
                
                # CAPTCHA should be exactly 4 digits
                if captcha_text and len(captcha_text) == 4:
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
            verification_code (str): Canvas-based verification code (if None, will read using OCR)
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

            # Handle verification code - READ USING OCR with retry logic
            if verification_code is None:
                max_retries = 3
                verification_code = None

                for attempt in range(1, max_retries + 1):
                    logger.info(f"Attempting to read CAPTCHA using OCR (attempt {attempt}/{max_retries})...")

                    # Try to read CAPTCHA from canvas
                    verification_code = self.read_captcha_from_canvas()

                    # If canvas OCR failed, try alternative methods
                    if not verification_code:
                        logger.info("Canvas OCR failed, trying alternative method...")
                        verification_code = self.read_captcha_from_img()

                    # If we successfully read it, break
                    if verification_code:
                        logger.info(f"✅ CAPTCHA read successfully using OCR: {verification_code}")
                        break
                    else:
                        logger.warning(f"Attempt {attempt} failed to read CAPTCHA")

                        # If not the last attempt, try to refresh CAPTCHA and retry
                        if attempt < max_retries:
                            logger.info("Refreshing CAPTCHA and trying again...")
                            self.refresh_captcha()
                            time.sleep(2)  # Wait for new CAPTCHA to load

                # If still failed after all retries, allow manual input as fallback
                if not verification_code:
                    logger.warning("❌ OCR failed to read CAPTCHA after all retries")
                    logger.info("Please manually enter the CAPTCHA code shown in the browser.")

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
            
            # Find all checkboxes - use simple working selectors
            checkbox_selectors = [
                "//input[@type='checkbox']",
                "//input[@class='ant-checkbox-input']",
                "//div[@class='ant-table-container']//input[@type='checkbox']",
                "//div[contains(@class, 'ant-table')]//input[@type='checkbox']"
            ]
            
            checkboxes = []
            for selector in checkbox_selectors:
                try:
                    checkboxes = self.driver.find_elements(By.XPATH, selector)
                    if checkboxes:
                        logger.info(f"Found {len(checkboxes)} checkboxes with selector: {selector}")
                        break
                except:
                    continue
            
            if not checkboxes:
                logger.warning("No checkboxes found - debugging page content...")
                # Debug: list all input elements
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
                    
                    # Check if we're on login page
                    if "login" in current_url:
                        logger.error("❌ Still on login page - need to login first!")
                        return 0
                    
                    # Check page title
                    page_title = self.driver.title
                    logger.info(f"Page title: {page_title}")
                    
                except Exception as e:
                    logger.warning(f"Error listing inputs: {e}")
                return 0
            
            # Count total visible checkboxes (cases)
            visible_checkboxes = [cb for cb in checkboxes if cb.is_displayed()]
            logger.info(f"📊 Total cases found: {len(visible_checkboxes)}")
            
            # Click ONLY the FIRST checkbox
            for i, checkbox in enumerate(visible_checkboxes):
                try:
                    if not checkbox.is_selected():
                        logger.info(f"🎯 Clicking FIRST checkbox (case {i+1})...")
                        
                        # Scroll to checkbox if needed
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                        time.sleep(0.2)
                        
                        # Try multiple click methods
                        try:
                            checkbox.click()
                        except:
                            # If normal click fails, try JavaScript click
                            self.driver.execute_script("arguments[0].click();", checkbox)
                        
                        logger.info(f"✅ First checkbox selected successfully")
                        return 1
                    else:
                        logger.info(f"Checkbox {i+1} already selected")
                        
                except Exception as e:
                    logger.warning(f"Failed to select first checkbox: {e}")
                    continue
            
            logger.info("No unselected checkboxes found")
            return 0
            
        except Exception as e:
            logger.error(f"Error selecting first checkbox: {e}")
            return 0
    
    def enable_switch_button(self):
        """
        Enable the switch button if it exists and is disabled
        Returns True if switch was found and enabled, False otherwise
        """
        try:
            # Look for the ant-switch button
            switch_selectors = [
                "//button[@role='switch']",
                "//button[contains(@class, 'ant-switch')]",
                "button[role='switch']",
                "button.ant-switch"
            ]
            
            switch_button = None
            for selector in switch_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for element in elements:
                        if element.is_displayed():
                            switch_button = element
                            logger.info(f"Found switch button with selector: {selector}")
                            break
                    
                    if switch_button:
                        break
                except:
                    continue
            
            if switch_button:
                # Check if switch is already enabled (aria-checked="true")
                aria_checked = switch_button.get_attribute("aria-checked")
                if aria_checked == "true":
                    logger.info("Switch button is already enabled")
                    return True
                else:
                    logger.info("Switch button is disabled, enabling it...")
                    # Scroll to button
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", switch_button)
                    time.sleep(0.2)
                    
                    # Click the switch to enable it
                    try:
                        switch_button.click()
                        logger.info("✅ Switch button enabled successfully")
                        return True
                    except:
                        # If normal click fails, try JavaScript click
                        self.driver.execute_script("arguments[0].click();", switch_button)
                        logger.info("✅ Switch button enabled with JavaScript")
                        return True
            else:
                logger.warning("Switch button not found - may not exist on this page")
                return False
                
        except Exception as e:
            logger.error(f"Error enabling switch button: {e}")
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

    def continuous_monitor(self, interval_seconds=1, username=None, password=None):
        """
        Continuously monitor for new cases with specified interval
        Args:
            interval_seconds (int): Time between checks in seconds (default: 1)
            username (str): Username for auto-login if session expires
            password (str): Password for auto-login if session expires
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
                    logger.warning("❌ Not logged in - session expired or logged out")

                    # Only attempt auto-login if credentials are provided
                    if username and password:
                        logger.info("Attempting to re-login automatically...")

                        # Try to login automatically
                        try:
                            login_success = self.login(username, password)
                            if login_success:
                                logger.info("✅ Successfully logged in again")
                                time.sleep(3)  # Wait for redirect

                                # Navigate back to forum page
                                self.driver.get(self.base_url)
                                time.sleep(2)
                                continue
                            else:
                                logger.error("❌ Auto-login failed")
                        except Exception as e:
                            logger.error(f"Error during auto-login: {e}")

                    # If auto-login failed or no credentials provided, wait for manual login
                    logger.info("Please login manually in the browser window")
                    time.sleep(10)  # Wait for manual login

                    # Navigate back to forum page after manual login
                    self.driver.get(self.base_url)
                    time.sleep(2)
                    continue

                # Check for checkboxes (cases) - use same selectors as select_first_checkbox
                try:
                    # Use the same selectors as select_first_checkbox function - simple working selectors
                    checkbox_selectors = [
                        "//input[@type='checkbox']",
                        "//input[@class='ant-checkbox-input']",
                        "//div[@class='ant-table-container']//input[@type='checkbox']",
                        "//div[contains(@class, 'ant-table')]//input[@type='checkbox']"
                    ]

                    checkboxes = []
                    for selector in checkbox_selectors:
                        try:
                            checkboxes = self.driver.find_elements(By.XPATH, selector)
                            if checkboxes:
                                logger.info(f"Found {len(checkboxes)} checkboxes with selector: {selector}")
                                break
                        except:
                            continue

                    # Count visible checkboxes properly
                    visible_checkboxes = [cb for cb in checkboxes if cb.is_displayed()]
                    current_case_count = len(visible_checkboxes)
                    logger.info(f"📊 Total cases found: {current_case_count}")

                    # Debug: show details of each checkbox
                    for i, cb in enumerate(visible_checkboxes):
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

                        # First, try to enable the switch button if it exists
                        self.enable_switch_button()

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
        bot.continuous_monitor(1, username, password)  # 1 second intervals with credentials

    except Exception as e:
        logger.error(f"Bot execution failed: {e}")
    finally:
        bot.close()


if __name__ == "__main__":
    main()

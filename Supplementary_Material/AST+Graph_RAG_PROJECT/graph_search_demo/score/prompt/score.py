"""
accuracy（准确性）
Relevance（相关性）：评价答案与问题或输入的相关性。
Fluency（流畅性）：评价生成的文本是否自然流，符合语言习惯。
Completeness（完整性）：评价答案的完整性，是否包含了足够的信息。
Cohesion（连贯性）：评价生成的文本内部是否一致连贯。
Conciseness（简明性）：评价答案是否简洁明了，不啰嗦。

Score 1: 完全不相关的答案，最差的回答。
Score 10: 完全准确且完美对齐的回答，最好的回答。
"""

EXAMPLE_STR = """
# 示例已脱敏，请按你自己的代码库填写评分示例。
"""


EXAMPLE_STR2 = """
--- eg: 1 ---
问题: 如何实现带参数的返回页面

参考答案: 
FOXPureComponent
<Button>
ajx.navigator.back(paramJSONStr, "target_page_id")

回答: 要在AJX框架中实现带参数的返回页面，可以使用 `ajx.navigator.back` 方法。这个方法允许你传递参数返回到指定的AJX页面。以下是具体的步骤和代码示例：

### 步骤
1. **准备参数**：将要传递的参数转换为JSON字符串。
2. **调用 `ajx.navigator.back` 方法**：传递参数和目标页面的 `pageId`（如果需要返回到特定页面）。

### 示例代码
```javascript
import * as AJX from '@framework/FOXRax.js';
import FOXPureComponent from '@framework/FOXPureComponent.jsx';
import Button from '@framework/Button.jsx';

export default class DemoBackWithParams extends FOXPureComponent {
    handleBack = () => {
        // 准备参数
        let paramObj = {
            "id": 1000,
            "name": "example"
        };
        let paramJSONStr = JSON.stringify(paramObj);

        // 调用 ajx.navigator.back 方法
        ajx.navigator.back(paramJSONStr, "target_page_id");
    }

    render() {
        return (
            <div>
                <Button onClick={this.handleBack}>返回并传递参数</Button>
            </div>
        );
    }
}
```

评分: {
    "reasoning": "标准答案命中了FOXPureComponent和<Button>标签，同时包含了ajx.navigator.back方法, 参数为paramJSONStr和target_page_id。回答的内容包含标准中所提到的关键元素，且扩展了很多标准答案以外的信息描述，补充信息对于回答问题有正向作用。Rating: 回答匹配到了参考答案中 100% 的元素,所以回答评分为 10分",
    "score": 10
}

--- eg: 2 ---
问题: 如何实现带参数的返回页面

参考答案: 
FOXPureComponent
<Button>
ajx.navigator.back(paramJSONStr, "target_page_id")

回答: 要在AJX框架中实现带参数的返回页面，可以使用 `ajx.navigator.back` 方法。这个方法允许你传递参数返回到指定的AJX页面。以下是具体的步骤和代码示例：

### 步骤
1. **准备参数**：将要传递的参数转换为JSON字符串。
2. **调用 `ajx.navigator.back` 方法**：传递参数和目标页面的 `pageId`（如果需要返回到特定页面）。

### 示例代码
```javascript
import * as AJX from '@framework/FOXRax.js';
import FOXPureComponent from '@framework/FOXPureComponent.jsx';
import Button from '@framework/Button.jsx';

export default class DemoBackWithParams extends FOXPureComponent {
    handleBack = () => {
        // 准备参数
        let paramObj = {
            "id": 1000,
            "name": "example"
        };
        let paramJSONStr = JSON.stringify(paramObj);

        // 调用 ajx.navigator.back 方法
        ajx.navigator.back();
    }

    render() {
        return (
            <div>
                <Button onClick={this.handleBack}>返回并传递参数</Button>
            </div>
        );
    }
}
```

评分: {
    "reasoning": "标准答案命中了FOXPureComponent和<Button>标签，同时包含了ajx.navigator.back方法, 但是缺少参数paramJSONStr和target_page_id。Rating: 回答匹配到了参考答案中 80% 的元素，所以回答评分为 8分",
    "score": 8
}

--- eg: 3 ---
问题: 如何实现带参数的返回页面

参考答案: 
FOXPureComponent
<Button>
ajx.navigator.back(paramJSONStr, "target_page_id")

回答: 要在AJX框架中实现带参数的返回页面，可以使用 `ajx.navigator.back` 方法。这个方法允许你传递参数返回到指定的AJX页面。以下是具体的步骤和代码示例：

### 步骤
1. **准备参数**：将要传递的参数转换为JSON字符串。
2. **调用 `ajx.navigator.back` 方法**：传递参数和目标页面的 `pageId`（如果需要返回到特定页面）。

### 示例代码
```javascript
import * as AJX from '@framework/FOXRax.js';
import FOXPureComponent from '@framework/FOXPureComponent.jsx';

export default class DemoBackWithParams extends FOXPureComponent {
    handleBack = () => {
        // 准备参数
        let paramObj = {
            "id": 1000,
            "name": "example"
        };
        let paramJSONStr = JSON.stringify(paramObj);

        // 调用 ajx.navigator.back 方法
        ajx.navigator.back();
    }

    render() {
        return (
            <div>
            </div>
        );
    }
}
```

评分: {
    "reasoning": "标准答案命中了FOXPureComponent和<Button>标签，同时包含了ajx.navigator.back方法, 但是缺少参数paramJSONStr和target_page_id。Rating: 回答匹配到了参考答案中 50%左右 的元素，所以此回答的评分为 5 分。",
    "score": 5
}

--- eg: 4 ---
问题: 如何实现带参数的返回页面

参考答案: 
FOXPureComponent
<Button>
ajx.navigator.back(paramJSONStr, "target_page_id")

回答: 要在AJX框架中实现带参数的返回页面，可以使用 `ajx.navigator.back` 方法。这个方法允许你传递参数返回到指定的AJX页面。以下是具体的步骤和代码示例：

### 步骤
1. **准备参数**：将要传递的参数转换为JSON字符串。
2. **调用 `ajx.navigator.back` 方法**：传递参数和目标页面的 `pageId`（如果需要返回到特定页面）。

### 示例代码
```javascript
import * as AJX from '@framework/FOXRax.js';
import FOXPureComponent from '@framework/FOXPureComponent.jsx';

export default class DemoBackWithParams extends FOXPureComponent {
    handleBack = () => {
        // 准备参数
        let paramObj = {
            "id": 1000,
            "name": "example"
        };
        let paramJSONStr = JSON.stringify(paramObj);

        // 假设存在back方法
        back();
    }

    render() {
        return (
            <div>
            </div>
        );
    }
}
```

评分: {
    "reasoning": "标准答案命中了FOXPureComponent标签，但是回答假设存在back方法， 这引入了额外不确定性。所以此回答的评分为 2 分",
    "score": 2
}
"""


# labeled_score_string
ACCURACY_CRITERIA = {
    "accuracy": """
        Score 1: 回答中没有直接匹配参考答案中的任何关键元素，即使回答包含了与问题相关的详细和准确的信息描述，也无法得高分。只要没有匹配到参考答案中的关键元素，即判定为 1 分。

        Score 2: 回答包含了参考答案中的元素，但其中明确出现了"假设"、"假如"等不确定性词语，引入了不稳定性。

        Score 5: 回答直接匹配参考答案中的 50% 的元素，部分关键元素丢失。

        Score 10: 回答直接匹配参考答案中的全部元素，即使有很多参考答案之外的其他元素，只要这些元素不影响回答的清晰性和合理性。参考答案中的每个元素需要作为独立的元素进行匹配。
    """,
    "rules": """
        1. 请确保完整阅读了全部内容，不要遗漏任何和参考答案中元素相关的内容。
        2. 参考答案中的每一项需要作为独立的元素做匹配。除非明确标识元素是作为部分，否则不能作为其他整体的部分匹配。例如：this.people.getAge 可以匹配到关键元素 getAge，但是 this.people.getAgeList 不能匹配元素 getAge。这非常重要！！
        3. 如果回复中包括大量事实真相之外没有要求的附加信息和方法，不作为减分标准。
        4. 当回答中明确出现"假设"、"假如"之类不确定性的词语时，要作为减分标准。
        5. 参考答案中的元素可能为文件（回答中对应带.js等后缀）、类名、函数名、方法名等，都可以与关键元素匹配。
    """,
    # "example": EXAMPLE_STR,
    "example": EXAMPLE_STR2,
}

# Score 1: 答案和参考答案完全不相关，没有任何关键词匹配，关键的文件及类都没有使用到。
# Score 2: 答案和参考答案相关，但是全文没有匹配到参考答案中的关键元素。
# Score 3: 答案和参考答案相关，使用到了参考答案中的大部分元素，但其中明确出现了"假设"、"假如"等不确定因素。
# Score 6: 答案和参考答案相关，使用到了大部分参考答案中的文件和类，代码结构较为合理但有改进空间。
# Score 9: 答案和参考答案高度相关，全部使用到了参考答案中的文件和类，引入了非常多的额外元素补充描述。
# Score 10: 答案和参考答案高度相关，全部使用到了参考答案中的文件和类，回答简单清晰，且代码结构合理。


# 补充信息，关键词
KWARGS = {
    "background": "你是一名专业的前端开发工程师，精通前端开发的各种知识，且对前端规范有深入的了解。负责开发前端业务功能。",
}

import React from 'react';

const IndexSection__structures2: React.FC = () => {
    return (
        <div className="flex flex-wrap -mx-4 -mb-4 md:mb-0">
  <div className="w-full md:w-2/3 px-4 mb-4 md:mb-0">
    <div className="mb-6 px-5">
      <textarea className="w-full text-coolGray-500 leading-tight placeholder-coolGray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 border border-coolGray-200 rounded-lg shadow-xs" name="field-name" rows={3} placeholder="Your question ..." id="question" defaultValue={""} />
      <label className="block mb-2 text-coolGray-800 font-medium" htmlFor="question">
      </label>
    </div>
  </div>
  <div className="w-full md:w-1/3 px-4 mb-4 md:mb-0">
    <div className="container mx-auto">
      <button className="inline-block py-3 px-7 w-full md:w-auto text-lg leading-7 text-blue-50 bg-blue-500 hover:bg-blue-600 font-medium text-center focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 border border-transparent rounded-md shadow-sm" type="submit">Submit</button>
    </div>
  </div>
</div>


    );
};

export default IndexSection__structures2;
